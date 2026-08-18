# Second Brain — Design Specification

Product of a design-interview session (2026-08-18). Every decision below was
made explicitly; this file is the reference for why the system is shaped the
way it is. Change the system → update this spec.

## Goal

A team-shareable second brain for a banking batch-operations domain
(Control-M chains/jobs, business documents, operational knowledge) that
answers **any question about the domain**, operated entirely through
**GitHub Copilot in VS Code**.

## Hard constraints

| Constraint | Consequence |
|------------|-------------|
| No embeddings / no vector DB | Retrieval = indexes + keyword search (FTS5/BM25) + grep |
| No infrastructure to run or pay for | Single SQLite file + stdio MCP process; nothing hosted |
| Copilot is the only LLM | Distillation happens inside VS Code (librarian pass), never via API calls in scripts |
| Sources: docx/xlsx/csv + Control-M JSON exports | Deterministic conversion pipeline; exports arrive as manual file drops |
| Job code lives in GitHub repos | Inspected at query time via GitHub MCP, not ingested |
| Based on the [Cerebras KB architecture](https://www.cerebras.ai/blog/how-we-built-our-knowledge-base) | See "Cerebras adaptation" below |

## Decisions (from the interview)

1. **Scope**: answer any domain question — operational (chains, failures,
   dependencies, owners), documentation lookup, onboarding.
2. **Distribution**: one git repo with a GitHub remote; each teammate clones.
   Knowledge + tooling + Copilot config travel together; zero per-machine setup
   beyond `pip install -r requirements.txt`.
3. **Ingestion**: hybrid — deterministic scripts (`tools/ingest.py`) plus an
   `inbox/` drop-zone workflow. Single entry point: the `/ingest` prompt in
   Copilot agent mode (runs the script, then distills).
4. **Originals**: converted documents are deleted from `inbox/` (a
   `source_file` pointer remains in frontmatter). **Control-M JSON exports are
   committed** to `knowledge/chains/definitions/` — text, diffable, and the
   ground truth chain cards are regenerated from.
5. **Control-M treatment**: never raw JSON as knowledge — a generated
   **chain card** per folder (jobs, schedule, internal flow, external in/out
   events, notifications, owners) plus cross-reference indexes. Restart/rerun
   instructions are a first-class card section, initially PENDIENTE; the
   librarian pass nags for them.
6. **Retrieval**: SQLite **FTS5** (BM25, `unicode61 remove_diacritics 2` —
   accent-insensitive, no language stemming) exposed through a **local MCP
   server** with five narrow tools: `search_kb`, `get_chain`, `find_job`,
   `who_owns`, `recent_changes`. Grep + index files are the always-available
   fallback. Org policy confirmed: local MCP and GitHub MCP are allowed.
7. **Copilot surface, layered** (graceful degradation across Business +
   Enterprise seats): `copilot-instructions.md` (works everywhere) →
   `kb-retrieval` skill + `second-brain` custom agent → MCP tools.
8. **Freshness**: manual re-ingest for now (`/ingest` when something changes);
   `recent_changes` (git-log-based) implements "knowledge expires". A
   scheduled CI ingest can be bolted on later without redesign.
9. **Language**: artifacts stay in their source language (mostly Spanish,
   some English); the index is accent/language-neutral; the agent answers in
   the asker's language, Spanish by default.
10. **Vocabulary is discovered, not predefined**: the librarian pass grows
    `indexes/_glossary.md`, `_systems.md`, `_owners.md` from whatever the
    ingested content mentions. The domain model is emergent.
11. **Runtime**: Python (team standard), stdlib SQLite; deps limited to
    mammoth, openpyxl, pyyaml, mcp.

## Cerebras adaptation

The referenced blog describes an embeddings-heavy hybrid RAG system
(Postgres + pgvector). That conflicts with the no-embeddings constraint, so
this system keeps its **transferable principles** and substitutes the vector
half with keyword search (decision: substitute, not just omit):

| Cerebras | Here |
|----------|------|
| Distillation before indexing (never index raw content) | Librarian pass: summaries, tags, chain cards |
| `subsystem_index` (precomputed summaries) | `indexes/_*.md` navigation maps, read first |
| `search_code` (ripgrep) | Copilot agent grep over `knowledge/` |
| Postgres GIN full-text | SQLite FTS5 + BM25 |
| Age decay / "knowledge expires" | git dates + `recent_changes` tool |
| Narrow MCP tools, client owns reasoning | 5-tool MCP server, no synthesis server-side |
| pgvector embeddings + RRF | **dropped** — substituted by FTS5 keyword retrieval |

## Known debt / open items

- `tools/chaincard.py` is built against the documented Control-M Automation
  API format, **unverified against a real export** (none was available at
  design time). Unrecognized elements surface in the card's "Elementos no
  interpretados" section; review it on the first real ingest and adapt.
- Repo visibility: created public; must be **private before the first real
  ingest** (internal banking operational data).
- Scale unknown (chains/docs counts never confirmed); FTS5 comfortably covers
  team-KB scale, revisit only if grep/FTS demonstrably misses.
