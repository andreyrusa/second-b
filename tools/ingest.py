"""Deterministic ingest: inbox/ -> knowledge/ (markdown + frontmatter) + FTS index.

Usage:
    python tools/ingest.py              # convert inbox, rebuild index
    python tools/ingest.py --keep      # do not delete originals from inbox
    python tools/ingest.py --dry-run   # report what would happen, touch nothing
    python tools/ingest.py --reindex   # only rebuild .index/kb.sqlite

This script is the faithful, reproducible layer: it never invents content.
The distillation layer (summaries, systems, owners, glossary, indexes/_*.md)
is Copilot's job — run the /ingest prompt after this script (the prompt runs
this script for you in agent mode).
"""

from __future__ import annotations

import argparse
import csv
import datetime
import re
import shutil
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import chaincard
import kb_index

REPO_ROOT = Path(__file__).resolve().parent.parent
INBOX = REPO_ROOT / "inbox"
DOCS_DIR = REPO_ROOT / "knowledge" / "docs"
CHAINS_DIR = REPO_ROOT / "knowledge" / "chains"
DEFINITIONS_DIR = CHAINS_DIR / "definitions"

MAX_TABLE_ROWS = 300  # cap converted spreadsheet/csv rows; the source is the truth


def slugify(name: str) -> str:
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text) or "documento"


def frontmatter(title: str, doc_type: str, source_file: str, extra: dict | None = None) -> str:
    today = datetime.date.today().isoformat()
    lines = [
        "---",
        f"title: {title}",
        f"type: {doc_type}",
        f"source_file: {source_file}",
        'source: ""  # origen (ruta compartida, quién lo envió…) — completar',
        f"ingested: {today}",
        "status: needs-distillation",
        'summary: ""',
        "systems: []",
        "owners: []",
        "tags: []",
    ]
    for key, value in (extra or {}).items():
        lines.append(f"{key}: {value}")
    lines.append("---\n")
    return "\n".join(lines)


def unique_target(directory: Path, stem: str, suffix: str = ".md") -> Path:
    target = directory / f"{stem}{suffix}"
    n = 2
    while target.exists():
        target = directory / f"{stem}-{n}{suffix}"
        n += 1
    return target


def _read_text_guessing(path: Path) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _rows_to_markdown(rows: list[list[str]], out: list[str]) -> None:
    if not rows:
        out.append("_Vacío._")
        return
    header, *body = rows
    header = [str(c).strip() or " " for c in header]
    out.append("| " + " | ".join(c.replace("|", "\\|") for c in header) + " |")
    out.append("|" + "---|" * len(header))
    for row in body[:MAX_TABLE_ROWS]:
        cells = [str(c).replace("|", "\\|").replace("\n", " ") for c in row]
        cells += [""] * (len(header) - len(cells))
        out.append("| " + " | ".join(cells[:len(header)]) + " |")
    if len(body) > MAX_TABLE_ROWS:
        out.append(f"\n_… {len(body) - MAX_TABLE_ROWS} filas más; "
                   "consultar el fichero de origen._")


def convert_docx(path: Path) -> str:
    import mammoth
    with path.open("rb") as fh:
        result = mammoth.convert_to_markdown(fh)
    body = result.value
    if result.messages:
        notes = "\n".join(f"<!-- mammoth: {m.message} -->" for m in result.messages)
        body = notes + "\n\n" + body
    return body


def convert_xlsx(path: Path) -> str:
    import openpyxl
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    out: list[str] = []
    for sheet in wb.worksheets:
        out.append(f"## Hoja: {sheet.title}\n")
        rows = [["" if c is None else c for c in row]
                for row in sheet.iter_rows(values_only=True)]
        rows = [r for r in rows if any(str(c).strip() for c in r)]
        _rows_to_markdown(rows, out)
        out.append("")
    wb.close()
    return "\n".join(out)


def convert_csv(path: Path) -> str:
    text = _read_text_guessing(path)
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows = [list(r) for r in csv.reader(text.splitlines(), dialect)]
    out: list[str] = []
    _rows_to_markdown(rows, out)
    return "\n".join(out)


def ingest_document(path: Path, dry_run: bool) -> tuple[Path, str] | None:
    suffix = path.suffix.lower()
    if suffix == ".docx":
        body = convert_docx(path)
    elif suffix in (".xlsx", ".xlsm"):
        body = convert_xlsx(path)
    elif suffix == ".csv":
        body = convert_csv(path)
    elif suffix in (".md", ".txt"):
        body = _read_text_guessing(path)
    else:
        return None
    target = unique_target(DOCS_DIR, slugify(path.stem))
    if not dry_run:
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        target.write_text(
            frontmatter(path.stem, "doc", path.name) + "\n" + body + "\n",
            encoding="utf-8",
        )
    return target, "convertido"


def ingest_controlm_json(path: Path, dry_run: bool) -> list[Path] | None:
    """Returns card paths, or None if the JSON is not Control-M shaped."""
    chains = chaincard.try_parse_file(path)
    if not chains:
        return None
    today = datetime.date.today().isoformat()
    definition_target = unique_target(DEFINITIONS_DIR, slugify(path.stem), ".json")
    definition_rel = definition_target.relative_to(REPO_ROOT).as_posix()
    cards = []
    for chain in chains:
        card_path = unique_target(CHAINS_DIR, slugify(chain.name))
        if not dry_run:
            CHAINS_DIR.mkdir(parents=True, exist_ok=True)
            card_path.write_text(
                chaincard.render_card(chain, definition_rel, today), encoding="utf-8")
        cards.append(card_path)
    if not dry_run:
        DEFINITIONS_DIR.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), definition_target)  # exports stay committed: ground truth
    return cards


def run(keep: bool, dry_run: bool) -> None:
    if not INBOX.exists():
        print("No existe inbox/ — nada que ingerir.")
        return
    created: list[str] = []
    skipped: list[str] = []
    errors: list[str] = []

    for path in sorted(p for p in INBOX.rglob("*") if p.is_file()):
        if path.name in (".gitkeep", "README.md"):
            continue
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            if path.suffix.lower() == ".json":
                cards = ingest_controlm_json(path, dry_run)
                if cards is None:
                    skipped.append(f"{rel} — JSON sin formato Control-M reconocible")
                    continue
                created += [c.relative_to(REPO_ROOT).as_posix() for c in cards]
                continue  # the JSON was moved, never deleted
            result = ingest_document(path, dry_run)
            if result is None:
                skipped.append(f"{rel} — extensión no soportada")
                continue
            created.append(result[0].relative_to(REPO_ROOT).as_posix())
            if not keep and not dry_run:
                path.unlink()  # original replaced by markdown + source_file pointer
        except Exception as exc:  # keep ingesting the rest of the inbox
            errors.append(f"{rel} — {type(exc).__name__}: {exc}")

    prefix = "[dry-run] " if dry_run else ""
    print(f"{prefix}Creados ({len(created)}):")
    for c in created:
        print(f"  + {c}")
    if skipped:
        print(f"{prefix}Omitidos ({len(skipped)}):")
        for s in skipped:
            print(f"  - {s}")
    if errors:
        print(f"{prefix}Errores ({len(errors)}):")
        for e in errors:
            print(f"  ! {e}")

    if not dry_run:
        kb_index.build()
        if created:
            print("\nPASE DE BIBLIOTECARIO PENDIENTE — ficheros con "
                  "status: needs-distillation:")
            for c in created:
                print(f"  * {c}")
            print("Completar summary/systems/owners/tags, actualizar indexes/_*.md "
                  "y volver a ejecutar: python tools/ingest.py --reindex")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keep", action="store_true",
                        help="no borrar originales de inbox/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reindex", action="store_true",
                        help="solo reconstruir el índice FTS")
    args = parser.parse_args()
    if args.reindex:
        kb_index.build()
        return
    run(keep=args.keep, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
