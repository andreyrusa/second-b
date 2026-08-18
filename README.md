# Second Brain — batch operations knowledge base

Team knowledge base for a banking batch-operations domain: Control-M chains
and jobs, business documents (docx/xlsx/csv) and operational notes. Operated
entirely through **GitHub Copilot in VS Code**. Zero infrastructure, no
embeddings: knowledge is plain markdown, retrieval is indexes + SQLite FTS5 +
grep.

## Quickstart

```bash
git clone <this repo> && cd second-brain
python -m pip install -r requirements.txt
code .
```

Opening the folder in VS Code auto-registers the `second-brain` MCP server
(`.vscode/mcp.json`) — start it when VS Code asks.

**To add knowledge**: drop files (`.docx`, `.xlsx`, `.csv`, `.md`, `.txt`,
Control-M JSON exports) into `inbox/`, then run the **/ingest** prompt in
Copilot chat (agent mode). It converts, distills, updates the indexes,
rebuilds the search index and proposes a commit.

**To ask questions**: use the `second-brain` custom agent in Copilot chat, or
just ask — the baseline rules in `.github/copilot-instructions.md` apply to
every Copilot conversation in this workspace.

**Demo / smoke test** (synthetic data, safe to run anywhere):

```bash
python tools/demo_fixtures.py   # fake inbox content
python tools/ingest.py          # convert + index it
python tools/smoke_test_mcp.py  # exercise the 5 MCP tools over stdio
git clean -fd knowledge && git checkout -- knowledge  # discard demo output
```

## How it works

| Piece | Where | Role |
|-------|-------|------|
| Drop zone | `inbox/` | Transient; contents gitignored |
| Knowledge | `knowledge/docs/`, `knowledge/chains/`, `knowledge/notes/` | Markdown + YAML frontmatter, one artifact per file |
| Ground truth | `knowledge/chains/definitions/*.json` | Raw Control-M exports, committed |
| Navigation maps | `indexes/_*.md` | Chains, job→chain, systems, owners, glossary — agents read these first |
| Search index | `.index/kb.sqlite` | FTS5 (BM25, accent-insensitive), gitignored, rebuilt by ingest |
| Pipeline | `tools/ingest.py`, `tools/chaincard.py`, `tools/kb_index.py` | Deterministic conversion — never invents content |
| MCP server | `tools/mcp_server.py` | `search_kb`, `get_chain`, `find_job`, `who_owns`, `recent_changes` |
| Copilot layer | `.github/copilot-instructions.md`, `.github/skills/kb-retrieval/`, `.github/agents/second-brain.agent.md`, `.github/prompts/ingest.prompt.md` | Baseline rules → retrieval skill → persona → librarian workflow |

**Ingestion is two layers** (pattern borrowed from
[Cerebras' knowledge base](https://www.cerebras.ai/blog/how-we-built-our-knowledge-base)):
a deterministic script converts sources faithfully, then Copilot performs the
*librarian pass* — summaries, tags, owners, and vocabulary discovery into the
index files. Distillation is what makes keyword-only retrieval work.

**Retrieval degrades gracefully**: indexes + MCP tools where available; plain
grep over the same markdown everywhere else. A teammate with no MCP loses
speed, not answers.

## Known debt

- `tools/chaincard.py` was built against the documented Control-M Automation
  API JSON format but **not yet verified against a real export from this
  team's Control-M**. Anything unrecognized appears under "Elementos no
  interpretados" in the chain card instead of being dropped — when the first
  real export is ingested, review that section and adapt the parser.
- The index files (`indexes/_*.md`) and glossary start empty by design: the
  domain vocabulary is discovered ingest by ingest.
