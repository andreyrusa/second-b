"""Generate synthetic inbox fixtures (fake PAGOS domain) to demo/smoke-test
the pipeline. See README "Demo / smoke test" for the full sequence and how to
discard the generated knowledge afterwards."""
import csv
import json
import pathlib
import zipfile

import openpyxl

inbox = pathlib.Path(__file__).resolve().parent.parent / "inbox"
inbox.mkdir(exist_ok=True)

data = {
    "CDN_PAGOS_LIQUIDACION": {
        "Type": "Folder", "ControlmServer": "CTMPROD", "OrderMethod": "Manual",
        "Application": "PAGOS", "SubApplication": "LIQUIDACION",
        "Description": "Liquidacion diaria de pagos",
        "When": {"WeekDays": ["MON", "TUE", "WED", "THU", "FRI"], "FromTime": "0300"},
        "ExtraccionMovimientos": {
            "Type": "Job:Command", "Command": "/opt/batch/extraccion.sh PROD",
            "Host": "srvbatch01", "RunAs": "ctmuser", "Critical": True,
            "Description": "Extrae movimientos del core bancario",
            "eventsToAdd": {"Type": "AddEvents", "Events": [{"Event": "EXTRACCION-OK"}]},
        },
        "CargaFicheroSEPA": {
            "Type": "Job:Script", "FileName": "carga_sepa.py", "FilePath": "/opt/batch/sepa",
            "Host": "srvbatch02", "RunAs": "ctmuser",
            "eventsToWaitFor": {"Type": "WaitForEvents", "Events": [{"Event": "EXTRACCION-OK"}]},
            "eventsToAdd": {"Type": "AddEvents", "Events": [{"Event": "SEPA-CARGADO"}]},
            "Notification0": {"Type": "Notify:ExecutionEndsNotOK",
                              "Destination": "JobLog", "Message": "Avisar a equipo pagos"},
        },
        "SubValidacion": {
            "Type": "SubFolder",
            "ValidarTotales": {
                "Type": "Job:Command", "Command": "/opt/batch/validar_totales.sh",
                "Host": "srvbatch02",
                "eventsToWaitFor": {"Type": "WaitForEvents",
                                    "Events": [{"Event": "SEPA-CARGADO"}]},
            },
        },
        "FlujoPrincipal": {"Type": "Flow",
                           "Sequence": ["ExtraccionMovimientos", "CargaFicheroSEPA"]},
        "ObjetoRaro": {"Type": "Job:SAP:Custom", "Weird": True},
        "CosaDesconocida": {"Type": "Alien"},
    },
    "CDN_PAGOS_INFORMES": {
        "Type": "SimpleFolder", "ControlmServer": "CTMPROD", "Application": "PAGOS",
        "InformeDiario": {
            "Type": "Job:Command", "Command": "/opt/batch/informe.sh",
            "Host": "srvbatch03",
            "eventsToWaitFor": {"Type": "WaitForEvents",
                                "Events": [{"Event": "SEPA-CARGADO"}]},
        },
    },
}
(inbox / "export_pagos.json").write_text(json.dumps(data, indent=2), encoding="utf-8")

rows = [["Sistema", "Responsable", "Descripción"],
        ["SEPA", "María López", "Liquidación de transferencias"],
        ["CORE", "Equipo Núcleo", "Core bancario"]]
with open(inbox / "sistemas.csv", "w", newline="", encoding="cp1252") as fh:
    csv.writer(fh, delimiter=";").writerows(rows)

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Calendario"
ws.append(["Cadena", "Ventana", "SLA"])
ws.append(["CDN_PAGOS_LIQUIDACION", "03:00-06:00", "07:00"])
wb.save(inbox / "calendario batch.xlsx")

DOC_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
<w:body><w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
<w:r><w:t>Procedimiento de liquidacion</w:t></w:r></w:p>
<w:p><w:r><w:t>Si falla la carga SEPA, revisar el fichero en /data/sepa/in.</w:t></w:r></w:p>
</w:body></w:document>"""
CT = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/word/document.xml"
 ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1"
 Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument"
 Target="word/document.xml"/></Relationships>"""
with zipfile.ZipFile(inbox / "procedimiento.docx", "w") as z:
    z.writestr("[Content_Types].xml", CT)
    z.writestr("_rels/.rels", RELS)
    z.writestr("word/document.xml", DOC_XML)

print("fixtures ok")
