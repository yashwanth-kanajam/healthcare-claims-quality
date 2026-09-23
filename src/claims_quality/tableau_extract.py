"""Package an existing dashboard with a local Hyper extract for Tableau Public.

No Tableau account, publishing API, or upload is used. Native rendering remains
a separate acceptance check even when the extracted values reconcile.
"""

import csv
import json
import math
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path


def convert_dashboard(directory):
    directory = Path(directory)
    source = directory / "Data/dashboard.csv"
    with source.open(newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != ["panel", "label", "value", "unit"]:
            raise ValueError("Expected dashboard columns: panel,label,value,unit")
        rows = []
        for row in reader:
            if set(row) != set(reader.fieldnames) or any(v is None for v in row.values()):
                raise ValueError("Malformed dashboard row")
            value = float(row["value"])
            if not math.isfinite(value):
                raise ValueError("Dashboard values must be finite")
            rows.append([row["panel"], row["label"], value, row["unit"]])
    if not rows:
        raise ValueError("Dashboard must contain at least one row")
    root = ET.parse(directory / "Claims_Quality.twb").getroot()
    ds = root.find("datasources/datasource")
    if ds is None or ds.get("name") != "claims":
        raise ValueError("Expected generated claims datasource")
    try:
        from tableauhyperapi import (
            Connection,
            CreateMode,
            HyperProcess,
            Inserter,
            SqlType,
            TableDefinition,
            TableName,
            Telemetry,
        )
    except ImportError as error:
        raise ValueError('Install the optional Tableau dependency with pip install ".[tableau]"') from error
    table = TableDefinition(
        TableName("Extract", "Extract"),
        [
            TableDefinition.Column("panel", SqlType.text()),
            TableDefinition.Column("label", SqlType.text()),
            TableDefinition.Column("value", SqlType.double()),
            TableDefinition.Column("unit", SqlType.text()),
        ],
    )
    with tempfile.TemporaryDirectory(prefix=".tableau-extract-", dir=directory) as temporary:
        stage = Path(temporary)
        extract_path = stage / "dashboard.hyper"
        with HyperProcess(
            Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_dir": str(stage.resolve())}
        ) as hyper:
            with Connection(hyper.endpoint, str(extract_path), CreateMode.CREATE_AND_REPLACE) as connection:
                connection.catalog.create_schema("Extract")
                connection.catalog.create_table(table)
                with Inserter(connection, table) as inserter:
                    inserter.add_rows(rows)
                    inserter.execute()
                actual = connection.execute_list_query(
                    'SELECT "panel", "label", "value", "unit" FROM "Extract"."Extract"'
                )
                if sorted(actual) != sorted(rows):
                    raise ValueError("Extract values do not match dashboard source")
        root.set("version", "18.1")
        ds.set("version", "18.1")
        for old in ds.findall("extract"):
            ds.remove(old)
        extract = ET.SubElement(ds, "extract", {"enabled": "true", "count": "-1", "units": "records"})
        connection = ET.SubElement(
            extract,
            "connection",
            {
                "class": "hyper",
                "dbname": "Data/dashboard.hyper",
                "schema": "Extract",
                "access_mode": "readonly",
                "authentication": "auth-none",
                "default-settings": "yes",
            },
        )
        ET.SubElement(
            connection,
            "relation",
            {
                "name": "Extract",
                "table": "[Extract].[Extract]",
                "type": "table",
            },
        )
        ET.indent(root)
        xml = ET.tostring(root, encoding="utf-8", xml_declaration=True)
        package = stage / "Claims_Quality_Public.twbx"
        with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("Claims_Quality_Public.twb", xml)
            z.writestr("Data/dashboard.csv", source.read_bytes())
            z.write(extract_path, "Data/dashboard.hyper")
        # Source CSV and legacy workbook remain unchanged. Publish only after read-back succeeds.
        extract_path.replace(directory / "Data/dashboard.hyper")
        (directory / "Claims_Quality_Public.twb").write_bytes(xml)
        package.replace(directory / "Claims_Quality_Public.twbx")
    result = dict(
        rows=len(rows),
        extract_values_verified=True,
        tableau_rendering_verified=False,
        publishing_performed=False,
        workbook="Claims_Quality_Public.twbx",
    )
    (directory / "extract-validation.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
