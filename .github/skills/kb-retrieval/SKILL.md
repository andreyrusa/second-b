---
name: kb-retrieval
description: How to answer domain questions from this second-brain knowledge base — Control-M chains, jobs, business documents. Use whenever the user asks what a chain or job does, dependencies between chains, who owns something, where a file or process is documented, or how to recover from a batch failure.
---

# Retrieving from the second brain

The knowledge base is markdown under `knowledge/`, with navigation maps under
`indexes/`. There are no embeddings: retrieval is indexes + keyword search +
grep. Follow this procedure.

## Procedure

1. **Translate the question into domain vocabulary.** If it contains a term
   you don't recognize, look it up in `indexes/_glossary.md` first.
2. **Pick the entry point by question type:**

   | Question is about…                  | Start with                                  |
   |-------------------------------------|---------------------------------------------|
   | what a chain does / its schedule    | MCP `get_chain`, else `indexes/_chains.md`  |
   | a specific job, its dependencies    | MCP `find_job`, else `indexes/_jobs-to-chains.md` |
   | who owns / who to contact           | MCP `who_owns` + `indexes/_owners.md`       |
   | a system, business process, document| MCP `search_kb`, else `indexes/_systems.md` |
   | what changed recently               | MCP `recent_changes` (or `git log -- knowledge indexes`) |

3. **Search with several keyword variants** (Spanish AND English, with and
   without accents — the index ignores accents but files may use either
   language). `search_kb` returns snippets and paths; **read the full file at
   `path`** before answering — snippets are not enough.
4. **If MCP tools are unavailable**, grep instead:
   - chain cards: `knowledge/chains/*.md` (sections: Trabajos, Dependencias,
     Recuperación y rearranque, Propietarios)
   - events/dependencies: grep the event name across `knowledge/chains/`
     — a chain that *genera* the event feeds the chains that *esperan* it
   - raw truth: `knowledge/chains/definitions/*.json` (the actual Control-M
     export, when the card seems incomplete)
5. **Cross-chain dependency questions**: collect the "Eventos de entrada" and
   "Eventos de salida" sections of the involved chain cards and join them by
   event name. Entrada = depends on another chain; salida = others may depend
   on it.
6. **Job code questions**: chain cards list what each job executes (script
   path, command). To read the actual script, search for it in the team's
   GitHub repositories with the GitHub MCP tools.

## Answering rules

- **Cite paths** for every factual claim. Quote the exact schedule, command or
  event names rather than paraphrasing them.
- **Freshness**: knowledge expires. Check the `ingested`/git date of what you
  cite; if two sources conflict, prefer the recent one and mention both.
- **Gaps are answers too**: a chain card whose "Recuperación y rearranque"
  says PENDIENTE means the team hasn't captured it — say exactly that, and
  offer to record the user's answer in the card or in `knowledge/notes/`.
- **Answer in the asker's language** (team default: Spanish).
- Never invent a chain, job, event, owner or procedure that no file supports.
