"""Control-M Automation API JSON -> chain cards (markdown).

Built against the publicly documented Control-M Automation API job-definition
format (folders containing Job:* objects, Flow sequences and event objects).
KNOWN DEBT: not yet verified against a real export from this team's
Control-M — anything the parser does not recognize is listed in the card's
"Elementos no interpretados" section instead of being silently dropped.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

# Folder-level keys that are settings, not jobs/flows.
FOLDER_SETTING_KEYS = {
    "Type", "ControlmServer", "OrderMethod", "SiteStandard", "Application",
    "SubApplication", "RunAs", "When", "Description", "CreatedBy",
    "Variables", "AdjustEvents", "DaysKeepActiveIfNotOk", "DaysKeepActive",
    "Confirm", "Priority", "Rerun", "RerunLimit", "SiteStandardPolicy",
}

# Job-level keys we extract explicitly; the rest go to "extras".
JOB_KNOWN_KEYS = {
    "Type", "Command", "Script", "FileName", "FilePath", "Host", "RunAs",
    "Application", "SubApplication", "Description", "When", "Priority",
    "Critical", "Variables", "Confirm", "Rerun", "RerunLimit",
    "DocumentationUrl", "Documentation",
}

WHEN_LABELS = {
    "Schedule": "Calendario",
    "Months": "Meses",
    "MonthDays": "Días del mes",
    "WeekDays": "Días de la semana",
    "FromTime": "Desde",
    "ToTime": "Hasta",
    "DaysRelation": "Relación de días",
    "Calendars": "Calendarios",
    "RuleBasedCalendars": "Calendarios por regla",
    "SpecificDates": "Fechas concretas",
    "ConfirmationCalendars": "Calendarios de confirmación",
}


@dataclass
class Job:
    name: str
    type: str
    runs: str = ""              # command / script path / summary of what executes
    host: str = ""
    run_as: str = ""
    application: str = ""
    sub_application: str = ""
    description: str = ""
    when: dict = field(default_factory=dict)
    waits_for: list = field(default_factory=list)    # in-conditions (events)
    adds: list = field(default_factory=list)         # out-conditions (events)
    deletes: list = field(default_factory=list)
    notifications: list = field(default_factory=list)
    critical: bool = False
    priority: str = ""
    subfolder: str = ""         # dotted path if nested in SubFolders
    extras: dict = field(default_factory=dict)       # recognized-as-job but unknown keys


@dataclass
class Chain:
    name: str
    folder_type: str = ""
    server: str = ""
    order_method: str = ""
    application: str = ""
    sub_application: str = ""
    description: str = ""
    when: dict = field(default_factory=dict)
    jobs: list = field(default_factory=list)
    flows: list = field(default_factory=list)        # (flow_name, [sequence])
    unparsed: list = field(default_factory=list)     # (key, reason)


def _events_of(obj: dict) -> list[str]:
    events = obj.get("Events", [])
    out = []
    for e in events:
        if isinstance(e, dict) and "Event" in e:
            out.append(str(e["Event"]))
        else:
            out.append(json.dumps(e, ensure_ascii=False))
    return out


def _parse_job(name: str, obj: dict, subfolder: str) -> Job:
    jtype = obj.get("Type", "")
    job = Job(name=name, type=jtype, subfolder=subfolder)
    job.host = str(obj.get("Host", ""))
    job.run_as = str(obj.get("RunAs", ""))
    job.application = str(obj.get("Application", ""))
    job.sub_application = str(obj.get("SubApplication", ""))
    job.description = str(obj.get("Description", ""))
    job.when = obj.get("When", {}) if isinstance(obj.get("When"), dict) else {}
    job.critical = bool(obj.get("Critical", False))
    job.priority = str(obj.get("Priority", ""))

    if "Command" in obj:
        job.runs = str(obj["Command"])
    elif "FileName" in obj:
        path = str(obj.get("FilePath", "")).rstrip("/\\")
        job.runs = f"{path}/{obj['FileName']}" if path else str(obj["FileName"])
    elif "Script" in obj:
        script = str(obj["Script"])
        job.runs = script if len(script) <= 200 else script[:200] + " …[script embebido truncado]"
    elif jtype == "Job:Dummy":
        job.runs = "(dummy — solo sincronización)"

    for key, value in obj.items():
        if key in JOB_KNOWN_KEYS:
            continue
        if isinstance(value, dict):
            vtype = str(value.get("Type", ""))
            if vtype == "WaitForEvents":
                job.waits_for.extend(_events_of(value))
                continue
            if vtype == "AddEvents":
                job.adds.extend(_events_of(value))
                continue
            if vtype == "DeleteEvents":
                job.deletes.extend(_events_of(value))
                continue
            if vtype.startswith("Notify"):
                dest = value.get("Destination", value.get("To", ""))
                msg = value.get("Message", "")
                job.notifications.append(f"{vtype} → {dest}: {msg}".strip(": "))
                continue
        job.extras[key] = value
    return job


def _walk_folder(chain: Chain, obj: dict, subfolder: str = "") -> None:
    for key, value in obj.items():
        if key in FOLDER_SETTING_KEYS or key.startswith("Defaults"):
            continue
        if not isinstance(value, dict):
            if not subfolder:  # settings-like scalar at folder level
                chain.unparsed.append((key, f"valor escalar no reconocido: {value!r}"))
            continue
        vtype = str(value.get("Type", ""))
        if vtype.startswith("Job"):
            chain.jobs.append(_parse_job(key, value, subfolder))
        elif vtype == "Flow":
            chain.flows.append((key, [str(s) for s in value.get("Sequence", [])]))
        elif vtype in ("SubFolder", "Folder", "SimpleFolder"):
            child = f"{subfolder}.{key}" if subfolder else key
            _walk_folder(chain, value, child)
        else:
            chain.unparsed.append((key, f"Type no reconocido: {vtype or '(sin Type)'}"))


def parse_controlm(data: dict) -> list[Chain]:
    """Return one Chain per top-level folder. Empty list => not Control-M shaped."""
    chains = []
    for name, obj in data.items():
        if not isinstance(obj, dict):
            continue
        ftype = str(obj.get("Type", ""))
        if "Folder" not in ftype:
            continue
        chain = Chain(
            name=name,
            folder_type=ftype,
            server=str(obj.get("ControlmServer", "")),
            order_method=str(obj.get("OrderMethod", "")),
            application=str(obj.get("Application", "")),
            sub_application=str(obj.get("SubApplication", "")),
            description=str(obj.get("Description", "")),
            when=obj.get("When", {}) if isinstance(obj.get("When"), dict) else {},
        )
        _walk_folder(chain, obj)
        chains.append(chain)
    return chains


def _when_lines(when: dict) -> list[str]:
    lines = []
    for key, value in when.items():
        label = WHEN_LABELS.get(key, key)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        lines.append(f"- **{label}**: {value}")
    return lines


def _md_escape(text: str) -> str:
    return str(text).replace("|", "\\|").replace("\n", " ")


def render_card(chain: Chain, definition_relpath: str, ingested: str) -> str:
    """Render a chain card in Spanish with machine frontmatter."""
    lines = [
        "---",
        f"title: Cadena {chain.name}",
        "type: chain",
        f"chain: {chain.name}",
        f"application: {chain.application}",
        f"controlm_server: {chain.server}",
        f"source_file: {definition_relpath}",
        f"ingested: {ingested}",
        "status: needs-distillation",
        'summary: ""',
        "systems: []",
        "owners: []",
        "tags: []",
        "---",
        "",
        f"# Cadena {chain.name}",
        "",
        "## Resumen",
        "",
        chain.description or "_PENDIENTE — a completar en el pase de bibliotecario._",
        "",
        "## Datos generales",
        "",
        f"- **Tipo de carpeta**: {chain.folder_type}",
        f"- **Servidor Control-M**: {chain.server or '—'}",
        f"- **Aplicación**: {chain.application or '—'}"
        + (f" / {chain.sub_application}" if chain.sub_application else ""),
        f"- **Método de orden**: {chain.order_method or '—'}",
        "",
        "## Planificación",
        "",
    ]
    lines.extend(_when_lines(chain.when) or ["_Sin planificación a nivel de carpeta._"])

    lines += ["", "## Trabajos", "",
              "| # | Trabajo | Tipo | Ejecuta | Host | Crítico |",
              "|---|---------|------|---------|------|---------|"]
    for i, job in enumerate(chain.jobs, 1):
        name = f"{job.subfolder}/{job.name}" if job.subfolder else job.name
        crit = "sí" if job.critical else ""
        lines.append(
            f"| {i} | {_md_escape(name)} | {_md_escape(job.type)} | "
            f"{_md_escape(job.runs) or '—'} | {_md_escape(job.host) or '—'} | {crit} |"
        )

    for job in chain.jobs:
        lines += ["", f"### {job.name}", ""]
        if job.description:
            lines.append(f"{job.description}\n")
        detail = []
        if job.runs:
            detail.append(f"- **Ejecuta**: `{job.runs}`")
        if job.host:
            detail.append(f"- **Host**: {job.host}")
        if job.run_as:
            detail.append(f"- **Usuario (RunAs)**: {job.run_as}")
        if job.priority:
            detail.append(f"- **Prioridad**: {job.priority}")
        if job.subfolder:
            detail.append(f"- **Subcarpeta**: {job.subfolder}")
        if job.when:
            detail.append("- **Planificación propia**:")
            detail.extend("  " + l for l in _when_lines(job.when))
        if job.waits_for:
            detail.append(f"- **Espera eventos (entrada)**: {', '.join(job.waits_for)}")
        if job.adds:
            detail.append(f"- **Genera eventos (salida)**: {', '.join(job.adds)}")
        if job.deletes:
            detail.append(f"- **Borra eventos**: {', '.join(job.deletes)}")
        if job.notifications:
            detail.append("- **Notificaciones**: " + "; ".join(job.notifications))
        if job.extras:
            detail.append("- **Otros atributos**: "
                          + json.dumps(job.extras, ensure_ascii=False))
        lines.extend(detail or ["_Sin detalles adicionales._"])

    lines += ["", "## Dependencias", "", "### Flujo interno", ""]
    if chain.flows:
        for fname, seq in chain.flows:
            lines.append(f"- **{fname}**: " + " → ".join(seq))
    else:
        lines.append("_Sin objetos Flow; el orden viene dado solo por eventos._")

    waits = {e for j in chain.jobs for e in j.waits_for}
    adds = {e for j in chain.jobs for e in j.adds}
    internal = sorted(waits & adds)
    ext_in = sorted(waits - adds)
    ext_out = sorted(adds - waits)
    lines += ["", "### Eventos de entrada (dependencias de OTRAS cadenas)", ""]
    lines += [f"- `{e}`" for e in ext_in] or ["_Ninguno — la cadena arranca sola._"]
    lines += ["", "### Eventos de salida (otras cadenas pueden depender de estos)", ""]
    lines += [f"- `{e}`" for e in ext_out] or ["_Ninguno._"]
    if internal:
        lines += ["", "### Eventos internos (generados y consumidos dentro de la cadena)", ""]
        lines += [f"- `{e}`" for e in internal]

    lines += [
        "", "## Recuperación y rearranque", "",
        "_PENDIENTE — conocimiento del equipo: cómo rearrancar esta cadena tras",
        "un fallo, qué comprobar antes, a quién avisar. Completar en el pase de",
        "bibliotecario o cuando ocurra el primer incidente._",
        "", "## Propietarios y notificaciones", "",
    ]
    notif = [f"- {n}" for j in chain.jobs for n in j.notifications]
    lines.extend(notif or ["_PENDIENTE — sin destinatarios en la definición._"])

    if chain.unparsed:
        lines += ["", "## Elementos no interpretados", "",
                  "_El parser no reconoció estos elementos del JSON; revisar y",
                  "adaptar `tools/chaincard.py` si son relevantes:_", ""]
        lines += [f"- `{k}` — {reason}" for k, reason in chain.unparsed]

    lines += ["", "## Origen", "",
              f"- Definición: [`{definition_relpath}`](/{definition_relpath})",
              f"- Ingerido: {ingested}", ""]
    return "\n".join(lines)


def try_parse_file(path: Path) -> list[Chain]:
    """Parse a JSON file; [] if it is valid JSON but not Control-M shaped."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return []
    return parse_controlm(data)
