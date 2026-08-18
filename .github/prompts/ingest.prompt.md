---
mode: agent
description: Ingesta el contenido de inbox/ y ejecuta el pase de bibliotecario — conversión, destilación, índices y reindexado.
---

Ejecuta la ingesta completa del segundo cerebro. Trabaja sobre este
repositorio; no toques nada fuera de él.

## 1. Conversión determinista

Ejecuta en el terminal:

```
python tools/ingest.py
```

Lee la salida: ficheros creados, omitidos y errores. Si hay errores o el
parser reporta "Elementos no interpretados" en alguna ficha de cadena,
infórmalos al usuario al final (no los arregles en silencio).

## 2. Pase de bibliotecario (destilación)

Para **cada** fichero listado con `status: needs-distillation`:

1. Léelo entero.
2. Completa su frontmatter:
   - `summary`: una o dos frases, en el idioma del documento, escritas para
     que una búsqueda por palabras clave las encuentre (menciona sistemas,
     cadenas y procesos por su nombre).
   - `systems`: sistemas/aplicaciones que menciona.
   - `owners`: personas o equipos responsables, si el contenido los revela.
   - `tags`: 3–6 palabras clave útiles (incluye sinónimos español/inglés).
   - Cambia `status` a `distilled`.
3. **Descubre vocabulario**: cada sistema, término de negocio, equipo o
   persona nuevos que encuentres, añádelos a `indexes/_systems.md`,
   `indexes/_glossary.md` o `indexes/_owners.md` siguiendo el formato de cada
   fichero. El modelo del dominio se construye así, ingesta a ingesta.
4. Para fichas de cadena (`type: chain`), además:
   - Añade/actualiza su fila en `indexes/_chains.md`.
   - Añade sus trabajos a `indexes/_jobs-to-chains.md`.
   - Si "Recuperación y rearranque" está PENDIENTE, **pregunta al usuario**
     si conoce el procedimiento; si lo conoce, escríbelo en la ficha. Si no,
     déjalo PENDIENTE.

No inventes nada en la destilación: `summary` y los índices solo pueden decir
lo que el documento dice.

## 3. Reindexado y cierre

1. Ejecuta: `python tools/ingest.py --reindex`
2. Comprueba con `git status` / `git diff --stat` qué ha cambiado.
3. Resume al usuario: ficheros ingeridos, términos nuevos en los índices,
   pendientes (rearranques sin documentar, elementos no interpretados,
   errores) y propón un mensaje de commit. **No hagas commit** salvo que el
   usuario lo pida.
