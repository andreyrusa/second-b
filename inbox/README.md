# inbox/ — zona de entrada

Deja aquí los ficheros a ingerir: `.docx`, `.xlsx`, `.csv`, `.md`, `.txt` y
exportaciones JSON de Control-M. Después ejecuta el prompt **/ingest** en el
chat de Copilot (o `python tools/ingest.py` en un terminal).

- Los documentos se convierten a markdown en `knowledge/` y el original se
  **elimina** de aquí (queda la referencia `source_file` en el frontmatter).
- Los JSON de Control-M se **archivan** en `knowledge/chains/definitions/`
  como fuente de verdad y se generan sus fichas de cadena.

El contenido de esta carpeta está en `.gitignore`: nunca se suben binarios al
repositorio.
