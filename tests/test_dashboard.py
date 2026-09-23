import csv
import xml.etree.ElementTree as ET
import zipfile

from claims_quality import dashboard
from claims_quality.model import CATEGORIES


def test_sheet_filters_keep_different_units_separate():
    root = ET.fromstring(dashboard.workbook([], 15905.27, 288))
    expected = {"Reconciliation", "Monthly paid", "Cohort PMPM", "Quality findings"}
    sheets = root.findall("./worksheets/worksheet")
    actual = {s.find(".//filter/groupfilter").get("member").strip('"') for s in sheets}
    assert actual == expected
    names = {s.get("name") for s in sheets}
    zones = {z.get("name") for z in root.findall(".//zone") if z.get("name")}
    assert names == zones
    assert all(s.find(".//filter").get("column") == "[claims].[none:panel:nk]" for s in sheets)


def test_packaged_data_reconciles_to_sql(tmp_path, monkeypatch):
    # Full expanded evaluation is independently tested; avoid rerunning all 72 cases here.
    monkeypatch.setattr(
        dashboard,
        "build_expanded_report",
        lambda out: {"aggregate_metrics": [{"category": c, "tp": 0} for c in CATEGORIES]},
    )
    summary = dashboard.build_dashboard(tmp_path)
    with zipfile.ZipFile(tmp_path / "Claims_Quality.twbx") as z:
        assert z.testzip() is None
        root = ET.fromstring(z.read("Claims_Quality.twb"))
        conn = root.find(".//connection")
        path = conn.get("directory") + "/" + conn.get("filename")
        records = list(csv.DictReader(z.read(path).decode().splitlines()))
    values = {r["label"]: float(r["value"]) for r in records if r["panel"] == "Reconciliation"}
    assert values["Correct header total"] == values["Correct line total"] == summary["paid_cents"] / 100
    assert (
        round(sum(float(r["value"]) for r in records if r["panel"] == "Monthly paid") * 100)
        == summary["paid_cents"]
    )
    assert summary["member_months"] == 288
    assert summary["tableau_rendering_verified"] is False
