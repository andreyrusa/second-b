"""Second-brain MCP server (stdio) — narrow retrieval primitives, no synthesis.

Following the Cerebras pattern: tools return structured raw evidence; the
client agent (GitHub Copilot) owns the reasoning and the final answer.
Started automatically by VS Code via .vscode/mcp.json.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kb_index

try:  # mcp SDK >= 2.0
    from mcp.server import MCPServer
except ImportError:  # mcp SDK 1.x
    from mcp.server.fastmcp import FastMCP as MCPServer

mcp = MCPServer("second-brain")

_NO_INDEX = ("El índice .index/kb.sqlite no existe todavía. "
             "Ejecuta: python tools/ingest.py --reindex")


def _index_ready() -> bool:
    return kb_index.DB_PATH.exists()


@mcp.tool()
def search_kb(query: str, type: str = "", limit: int = 10) -> list[dict] | str:
    """Full-text (BM25) search over the whole knowledge base.

    Args:
        query: keywords in Spanish or English (diacritics optional).
        type: optional filter — "chain", "doc", "note" or "index".
        limit: max results (default 10).

    Returns a list of {path, title, type, updated, snippet, score}; lower
    score = better match. Read the file at `path` for the full content.
    """
    if not _index_ready():
        return _NO_INDEX
    return kb_index.search(query, doc_type=type or None, limit=limit)


@mcp.tool()
def get_chain(name: str) -> dict | str:
    """Get the full chain card for a Control-M chain (folder) by name.

    Accepts partial names. Returns {name, application, summary, path,
    card_markdown}; `path` also appears in the card's Origen section next to
    the raw JSON definition, which is the ground truth.
    """
    if not _index_ready():
        return _NO_INDEX
    hit = kb_index.get_chain(name)
    if not hit:
        return f"Ninguna cadena coincide con {name!r}. Prueba search_kb o find_job."
    card = (kb_index.REPO_ROOT / hit["path"]).read_text(encoding="utf-8")
    return hit | {"card_markdown": card}


@mcp.tool()
def find_job(job_name: str) -> list[dict] | str:
    """Locate a Control-M job by (partial) name across every chain.

    Returns a list of {name, chain, chain_path, runs, host, waits_for, adds} —
    waits_for/adds are the in/out events (conditions), i.e. the dependency
    edges toward other jobs and chains.
    """
    if not _index_ready():
        return _NO_INDEX
    hits = kb_index.find_job(job_name)
    return hits or f"Ningún trabajo coincide con {job_name!r}."


@mcp.tool()
def who_owns(entity: str) -> list[dict] | str:
    """Find the owner(s) of a chain, document, system or topic.

    Matches the `owners` frontmatter across the knowledge base. Returns
    {owner, path, title} rows. Also check indexes/_owners.md for context.
    """
    if not _index_ready():
        return _NO_INDEX
    hits = kb_index.who_owns(entity)
    return hits or (f"Sin propietario registrado para {entity!r}. "
                    "Revisa indexes/_owners.md o pregunta al equipo y regístralo.")


@mcp.tool()
def recent_changes(days: int = 14) -> str:
    """What changed in the knowledge base in the last N days (git history).

    Freshness signal: prefer recently-updated knowledge when sources conflict.
    """
    result = subprocess.run(
        ["git", "log", f"--since={days} days ago", "--date=short",
         "--pretty=format:%ad %s", "--name-status", "--",
         "knowledge", "indexes"],
        cwd=kb_index.REPO_ROOT, capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        if "does not have any commits" in result.stderr:
            return "El repositorio aún no tiene commits — sin historial que consultar."
        return f"git log falló: {result.stderr.strip()}"
    return result.stdout.strip() or f"Sin cambios en los últimos {days} días."


if __name__ == "__main__":
    mcp.run()  # stdio transport
