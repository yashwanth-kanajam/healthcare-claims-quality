"""Export SQL-backed Tableau inputs and a self-contained local workbook.

Workbook XML is generated, not rendered here. Opening the workbook is a separate
check; XML/ZIP validation cannot certify Tableau rendering.
"""

import csv
import json
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from .detect import detect, query
from .expanded import build_expanded_report
from .generate import generate, validate_clean


def element(parent, tag, text=None, **attributes):
    child = ET.SubElement(parent, tag, attributes)
    if text is not None:
        child.text = str(text)
    return child


def workbook(rows, paid, member_months):
    root = ET.Element(
        "workbook",
        {"version": "9.3", "source-platform": "mac", "source-build": "2026.2.2 (20262.26.0819.2015)"},
    )
    element(root, "preferences")
    sources = element(root, "datasources")
    ds = element(
        sources,
        "datasource",
        name="claims",
        caption="Reconciled synthetic claims",
        inline="true",
        version="9.3",
    )
    connection = element(ds, "connection", directory="Data", filename="dashboard.csv", server="")
    connection.set("class", "textscan")
    relation = element(connection, "relation", name="dashboard.csv", table="[dashboard#csv]", type="table")
    columns = element(relation, "columns", header="yes", separator=",", locale="en_US")
    columns.set("character-set", "UTF-8")
    fields = [("panel", "string"), ("label", "string"), ("value", "real"), ("unit", "string")]
    definitions = []
    for i, (name, kind) in enumerate(fields):
        element(columns, "column", name=name, datatype=kind, ordinal=str(i))
        definitions.append(
            dict(
                name="[" + name + "]",
                datatype=kind,
                role="measure" if kind == "real" else "dimension",
                type="quantitative" if kind == "real" else "nominal",
            )
        )
    element(ds, "aliases", enabled="yes")
    for definition in definitions:
        element(ds, "column", **definition)
    sheets = element(root, "worksheets")
    panels = [
        ("Reconciliation — USD", "Reconciliation"),
        ("Monthly paid — USD", "Monthly paid"),
        ("Age cohort — paid per member-month", "Cohort PMPM"),
        ("Expanded evaluation — true-positive units", "Quality findings"),
    ]
    for title, panel in panels:
        sheet = element(sheets, "worksheet", name=title)
        title_node = element(element(element(sheet, "layout-options"), "title"), "formatted-text")
        element(title_node, "run", title, fontsize="12", bold="true")
        table = element(sheet, "table")
        view = element(table, "view")
        element(
            element(view, "datasources"), "datasource", name="claims", caption="Reconciled synthetic claims"
        )
        deps = element(view, "datasource-dependencies", datasource="claims")
        for definition in definitions:
            column = element(deps, "column", **definition)
            if definition["name"] == "[label]":
                column.set("caption", "Category")
        for field, derivation, kind, suffix in [
            ("panel", "None", "nominal", "nk"),
            ("label", "None", "nominal", "nk"),
            ("value", "Sum", "quantitative", "qk"),
        ]:
            element(
                deps,
                "column-instance",
                column="[" + field + "]",
                derivation=derivation,
                name=f"[{derivation.lower()}:{field}:{suffix}]",
                pivot="key",
                type=kind,
            )
        filt = element(view, "filter", column="[claims].[none:panel:nk]")
        filt.set("class", "categorical")
        element(filt, "groupfilter", function="member", level="[none:panel:nk]", member='"' + panel + '"')
        element(element(view, "slices"), "column", "[claims].[none:panel:nk]")
        element(view, "aggregation", value="true")
        style = element(table, "style")
        rule = element(style, "style-rule", element="mark")
        element(rule, "format", attr="mark-labels-show", value="true")
        axis = element(style, "style-rule", element="axis")
        axis_title = (
            "True-positive units"
            if panel == "Quality findings"
            else ("Paid per member-month (USD)" if panel == "Cohort PMPM" else "Paid amount (USD)")
        )
        element(
            axis,
            "format",
            attr="title",
            field="[claims].[sum:value:qk]",
            scope="cols",
            value=axis_title,
            **{"class": "0"},
        )
        pane = element(element(table, "panes"), "pane")
        element(element(pane, "view"), "breakdown", value="auto")
        mark = element(pane, "mark")
        mark.set("class", "Bar")
        element(pane, "encodings")
        element(table, "rows", "[claims].[none:label:nk]")
        element(table, "cols", "[claims].[sum:value:qk]")
    dashboards = element(root, "dashboards")
    dashboard = element(dashboards, "dashboard", name="Claims quality and utilization")
    element(dashboard, "style")
    element(dashboard, "size", maxheight="900", maxwidth="1200", minheight="900", minwidth="1200")
    zones = element(dashboard, "zones")
    text = element(zones, "zone", id="1", x="1500", y="1000", w="97000", h="14000", **{"type-v2": "text"})
    formatted = element(text, "formatted-text")
    element(
        formatted,
        "run",
        f"SYNTHETIC CLAIMS | 2024\nReconciled paid: ${paid:,.2f}  •  Enrolled member-months: {member_months}\nControlled simulation. No clinical or real-payer performance claims.",
        fontsize="16",
        bold="true",
    )
    for i, (title, _panel) in enumerate(panels):
        element(
            zones,
            "zone",
            id=str(i + 2),
            name=title,
            x=str(1500 + (i % 2) * 49000),
            y=str(17000 + (i // 2) * 39000),
            w="47500",
            h="37000",
        )
    windows = element(root, "windows")
    window = element(windows, "window", name="Claims quality and utilization", maximized="true")
    window.set("class", "dashboard")
    points = element(window, "viewpoints")
    for title, _panel in panels:
        element(element(points, "viewpoint", name=title), "zoom", type="entire-view")
    element(window, "active", id="-1")
    ET.indent(root)
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_dashboard(out, seed=17):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    data = generate(seed)
    validate_clean(data)
    if detect(data):
        raise ValueError("Baseline has flags; dashboard refused")
    monthly = query(data, "utilization.sql")
    cohorts = query(data, "cohorts.sql")
    totals = query(data, "analytics.sql")[0]
    expanded = build_expanded_report(out / "evaluation")
    rows = []
    for label, key in [
        ("Incorrect header-line join", "incorrect_join_paid_cents"),
        ("Correct header total", "correct_header_paid_cents"),
        ("Correct line total", "correct_line_paid_cents"),
    ]:
        rows.append(dict(panel="Reconciliation", label=label, value=totals[key] / 100, unit="USD"))
    rows += [
        dict(panel="Monthly paid", label=r["month"][:7], value=r["paid_cents"] / 100, unit="USD")
        for r in monthly
    ]
    rows += [
        dict(
            panel="Cohort PMPM",
            label=r["cohort"],
            value=r["paid_per_member_month"],
            unit="USD per member-month",
        )
        for r in cohorts
    ]
    rows += [
        dict(
            panel="Quality findings",
            label={
                "exact_duplicate": "Exact duplicates",
                "broken_foreign_key": "Broken references",
                "invalid_date_sequence": "Invalid date sequences",
                "financial_reconciliation": "Financial reconciliation",
            }[r["category"]],
            value=r["tp"],
            unit="record-category-run units",
        )
        for r in expanded["aggregate_metrics"]
    ]
    (out / "Data").mkdir(exist_ok=True)

    def csv_file(path, records):
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(records[0]))
            writer.writeheader()
            writer.writerows(records)

    csv_file(out / "Data/dashboard.csv", rows)
    csv_file(out / "monthly.csv", monthly)
    csv_file(out / "cohorts.csv", cohorts)
    mm = sum(r["member_months"] for r in monthly)
    assert sum(r["paid_cents"] for r in monthly) == totals["correct_header_paid_cents"]
    assert sum(r["paid_cents"] for r in cohorts) == totals["correct_header_paid_cents"]
    xml = workbook(rows, totals["correct_header_paid_cents"] / 100, mm)
    (out / "Claims_Quality.twb").write_bytes(xml)
    with zipfile.ZipFile(out / "Claims_Quality.twbx", "w", zipfile.ZIP_DEFLATED) as z:
        for name, content in [
            ("Claims_Quality.twb", xml),
            ("Data/dashboard.csv", (out / "Data/dashboard.csv").read_bytes()),
        ]:
            info = zipfile.ZipInfo(name, date_time=(2024, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, content)
    summary = dict(
        seed=seed,
        claims=len(data["claim_headers"]),
        members=len(data["members"]),
        member_months=mm,
        paid_cents=totals["correct_header_paid_cents"],
        paid_per_member_month=totals["correct_header_paid_cents"] / 100 / mm,
        claims_per_1000_member_months=len(data["claim_headers"]) * 1000 / mm,
        tableau_rendering_verified=False,
    )
    (out / "dashboard-reconciliation.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
