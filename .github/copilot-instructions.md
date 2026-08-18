# Second brain — baseline rules

This repository is a team knowledge base ("second brain") for a banking batch
operations domain: Control-M chains and jobs, business documents, and
operational notes. Knowledge lives as markdown under `knowledge/`, navigation
maps under `indexes/`, tooling under `tools/`.

When answering questions about the domain:

1. **Indexes first.** Read the relevant `indexes/_*.md` file before searching:
   `_chains.md` (what each chain does), `_jobs-to-chains.md` (job lookup),
   `_systems.md`, `_owners.md`, `_glossary.md` (unknown terms).
2. **Then search.** Prefer the `second-brain` MCP tools (`search_kb`,
   `get_chain`, `find_job`, `who_owns`, `recent_changes`). If they are not
   available, grep `knowledge/` and `indexes/` directly.
3. **Cite every claim** with the file path it came from, e.g.
   `knowledge/chains/cdn_pagos_liquidacion.md`. If sources conflict, cite both
   and say which is more recent — never present a guess as fact.
4. **Answer in the language of the question.** The team works mainly in
   Spanish; knowledge artifacts may be in Spanish or English.
5. **Say when the knowledge base doesn't know.** Do not invent chains, jobs,
   owners or procedures. If the answer is missing, say so and suggest
   capturing it as a note in `knowledge/notes/`.
6. For questions about job *code* (scripts referenced by chain cards), follow
   the reference from the card into the corresponding GitHub repository using
   the GitHub MCP tools.

The detailed retrieval procedure is in
`.github/skills/kb-retrieval/SKILL.md`; the ingestion workflow is the
`/ingest` prompt.
