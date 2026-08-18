# Handoff — second-brain (2026-08-18)

For the next agent session continuing this project. Read this, then
`docs/SPEC.md` (full design record) and `README.md` (how it works / quickstart)
— their content is not repeated here.

## State: built, tested, pushed

Everything designed in the interview session is implemented and verified:

- Repo: https://github.com/andreyrusa/second-b (branch `master`, default;
  remote uses HTTPS via `gh` auth — SSH is not set up on this machine).
- Commits: `2102e1d` (full build), `f57bd4f` (spec). Working tree clean.
- Pipeline tested end-to-end with synthetic fixtures: `python
  tools/demo_fixtures.py && python tools/ingest.py && python
  tools/smoke_test_mcp.py` all pass (accent-insensitive FTS5 search, chain
  cards with subfolders/events/unknown-element reporting, all 5 MCP tools over
  real stdio JSON-RPC).
- Environment: Windows 11, Python 3.13.5 (spec says team standard 3.12 —
  code targets both), deps installed globally via pip. Note: `mcp` SDK 2.0
  renamed `FastMCP` → `MCPServer`; `tools/mcp_server.py` supports both.

## Immediate next steps (in priority order)

1. **Make the repo private** before any real data is ingested — it is PUBLIC
   and will hold internal banking operational data. User has been warned
   twice but has not decided. Command ready:
   `gh repo edit andreyrusa/second-b --visibility private`
2. **First real ingest**: user drops a real Control-M JSON export + a couple
   of documents into `inbox/`, runs `/ingest` in Copilot chat. Then review
   the generated chain card's "Elementos no interpretados" section and adapt
   `tools/chaincard.py` — the parser is built against the documented
   Automation API format but unverified against this team's exports (top
   known-debt item in the spec).
3. **Verify the Copilot layer actually loads** in the user's VS Code:
   `.github/copilot-instructions.md`, `.github/skills/kb-retrieval/SKILL.md`,
   `.github/agents/second-brain.agent.md`, `.github/prompts/ingest.prompt.md`,
   `.vscode/mcp.json`. File locations/frontmatter follow late-2025 VS Code
   conventions but were NOT validated against the user's actual VS Code
   version — if Copilot doesn't pick something up, check current docs for the
   expected paths (chatmodes vs agents, skills support flag) and adjust.
4. After the first successful librarian pass, sanity-check that
   `indexes/_*.md` got populated (vocabulary is discovered at ingest by
   design — decision 10 in the spec).

## Context that lives nowhere else

- User: andreyrusa (GitHub), Spanish-speaking banking batch-ops team; mixed
  Copilot Business + Enterprise seats; org policy allows local MCP servers
  and GitHub MCP (confirmed by user, not tested).
- Source docs arrive as manual file drops in a local dir (no SharePoint/API
  access assumed); Control-M exports likewise manual.
- The Cerebras blog the design is "founded on" returns HTTP 500; the
  architecture summary used during design came from secondary sources
  (mer.vin, stellarwork.com, slite.com) — see the adaptation table in the spec.
- A project memory exists in the Claude memory dir pointing at the spec and
  the two open warnings.

## Suggested skills for the next session

- `research` — to verify current VS Code Copilot customization file formats
  (skills/agents/prompts locations) if the Copilot layer doesn't load (step 3).
- `diagnose` — if the first real Control-M export breaks the parser in
  non-obvious ways.
- `code-review` — before the team starts depending on `tools/`, review the
  pipeline changes since `2102e1d`.
- `grilling` — if the user brings new requirements (e.g. scheduled ingestion,
  scale problems), re-enter interview mode rather than assuming.
