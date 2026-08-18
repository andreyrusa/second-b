"""SQLite FTS5 index over knowledge/ — build at ingest, query from the MCP server.

Zero infrastructure: one file at .index/kb.sqlite, rebuilt from scratch on every
ingest (the corpus is small; rebuild keeps the code trivial and the index honest).
Tokenizer: unicode61 with diacritics removal, so "planificacion" matches
"planificación" — no language-specific stemming (Spanish/English mixed corpus).
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
INDEXES_DIR = REPO_ROOT / "indexes"
DB_PATH = REPO_ROOT / ".index" / "kb.sqlite"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (frontmatter dict, body). Tolerates missing/broken frontmatter."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text
    try:
        meta = yaml.safe_load(match.group(1)) or {}
        if not isinstance(meta, dict):
            meta = {}
    except yaml.YAMLError:
        meta = {}
    return meta, text[match.end():]


def _as_list(value) -> list[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value in (None, ""):
        return []
    return [str(value)]


def connect(db_path: Path = DB_PATH) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def build(verbose: bool = True) -> dict:
    """Rebuild the whole index from knowledge/ and indexes/. Returns counts."""
    if DB_PATH.exists():
        DB_PATH.unlink()
    conn = connect()
    conn.executescript("""
        CREATE VIRTUAL TABLE kb USING fts5(
            title, summary, body, tags,
            path UNINDEXED, type UNINDEXED, updated UNINDEXED,
            tokenize = 'unicode61 remove_diacritics 2'
        );
        CREATE TABLE chains(
            name TEXT PRIMARY KEY, path TEXT, application TEXT, summary TEXT
        );
        CREATE TABLE jobs(
            name TEXT, chain TEXT, chain_path TEXT, runs TEXT, host TEXT
        );
        CREATE TABLE events(
            event TEXT, direction TEXT, job TEXT, chain TEXT
        );
        CREATE TABLE owners(
            owner TEXT, path TEXT, title TEXT
        );
    """)

    counts = {"documents": 0, "chains": 0, "jobs": 0}
    md_files = sorted(KNOWLEDGE_DIR.rglob("*.md")) + sorted(INDEXES_DIR.glob("*.md"))
    for path in md_files:
        text = path.read_text(encoding="utf-8")
        meta, body = parse_frontmatter(text)
        rel = path.relative_to(REPO_ROOT).as_posix()
        doc_type = str(meta.get("type", "index" if path.parent == INDEXES_DIR else "doc"))
        title = str(meta.get("title", path.stem))
        updated = str(meta.get("ingested", ""))
        tags = " ".join(_as_list(meta.get("tags")) + _as_list(meta.get("systems")))
        conn.execute(
            "INSERT INTO kb(title, summary, body, tags, path, type, updated) "
            "VALUES (?,?,?,?,?,?,?)",
            (title, str(meta.get("summary", "")), body, tags, rel, doc_type, updated),
        )
        counts["documents"] += 1

        for owner in _as_list(meta.get("owners")):
            conn.execute("INSERT INTO owners VALUES (?,?,?)", (owner, rel, title))

        if doc_type == "chain":
            chain_name = str(meta.get("chain", path.stem))
            conn.execute(
                "INSERT OR REPLACE INTO chains VALUES (?,?,?,?)",
                (chain_name, rel, str(meta.get("application", "")),
                 str(meta.get("summary", ""))),
            )
            counts["chains"] += 1
            counts["jobs"] += _index_chain_body(conn, chain_name, rel, body)

    conn.commit()
    conn.close()
    if verbose:
        print(f"Índice reconstruido: {counts['documents']} documentos, "
              f"{counts['chains']} cadenas, {counts['jobs']} trabajos "
              f"-> {DB_PATH.relative_to(REPO_ROOT)}")
    return counts


_JOB_ROW_RE = re.compile(r"^\|\s*\d+\s*\|([^|]+)\|([^|]+)\|([^|]+)\|([^|]+)\|")
_EVENT_LINE_RE = re.compile(
    r"\*\*(Espera eventos \(entrada\)|Genera eventos \(salida\))\*\*: (.+)$")


def _index_chain_body(conn: sqlite3.Connection, chain: str, rel: str, body: str) -> int:
    """Extract job and event rows from a rendered chain card."""
    jobs = 0
    current_job = ""
    for line in body.splitlines():
        row = _JOB_ROW_RE.match(line)
        if row and row.group(2).strip() != "Tipo":
            name = row.group(1).strip().lstrip("\\")
            conn.execute(
                "INSERT INTO jobs VALUES (?,?,?,?,?)",
                (name.split("/")[-1], chain, rel,
                 row.group(3).strip(), row.group(4).strip()),
            )
            jobs += 1
        if line.startswith("### "):
            current_job = line[4:].strip()
        ev = _EVENT_LINE_RE.search(line)
        if ev:
            direction = "in" if "entrada" in ev.group(1) else "out"
            for event in ev.group(2).split(","):
                conn.execute("INSERT INTO events VALUES (?,?,?,?)",
                             (event.strip(), direction, current_job, chain))
    return jobs


def _fts_query(raw: str) -> str:
    """User text -> safe FTS5 query: quoted tokens, implicit AND."""
    tokens = re.findall(r"\w+", raw, flags=re.UNICODE)
    return " ".join(f'"{t}"' for t in tokens) if tokens else '""'


def search(query: str, doc_type: str | None = None, limit: int = 10) -> list[dict]:
    """BM25 search; falls back to OR-matching when AND yields nothing."""
    conn = connect()
    try:
        for joiner in (" ", " OR "):
            tokens = re.findall(r"\w+", query, flags=re.UNICODE)
            if not tokens:
                return []
            fts = joiner.join(f'"{t}"' for t in tokens)
            sql = ("SELECT path, title, type, updated, "
                   "snippet(kb, 2, '**', '**', ' … ', 24) AS snippet, "
                   "bm25(kb, 4.0, 3.0, 1.0, 2.0) AS score "
                   "FROM kb WHERE kb MATCH ?")
            params: list = [fts]
            if doc_type:
                sql += " AND type = ?"
                params.append(doc_type)
            sql += " ORDER BY score LIMIT ?"
            params.append(limit)
            rows = [dict(r) for r in conn.execute(sql, params)]
            if rows or joiner == " OR ":
                return rows
        return []
    finally:
        conn.close()


def find_job(job_name: str) -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT name, chain, chain_path, runs, host FROM jobs "
            "WHERE name LIKE ? ORDER BY name LIMIT 25",
            (f"%{job_name}%",),
        ).fetchall()
        out = []
        for r in rows:
            events = conn.execute(
                "SELECT event, direction FROM events WHERE job LIKE ? AND chain = ?",
                (f"%{r['name']}%", r["chain"]),
            ).fetchall()
            out.append(dict(r) | {
                "waits_for": [e["event"] for e in events if e["direction"] == "in"],
                "adds": [e["event"] for e in events if e["direction"] == "out"],
            })
        return out
    finally:
        conn.close()


def get_chain(name: str) -> dict | None:
    conn = connect()
    try:
        row = conn.execute(
            "SELECT name, path, application, summary FROM chains "
            "WHERE name LIKE ? ORDER BY length(name) LIMIT 1",
            (f"%{name}%",),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def who_owns(entity: str) -> list[dict]:
    conn = connect()
    try:
        rows = conn.execute(
            "SELECT owner, path, title FROM owners "
            "WHERE owner LIKE ? OR title LIKE ? OR path LIKE ? LIMIT 25",
            (f"%{entity}%", f"%{entity}%", f"%{entity}%"),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    build()
