import csv
import xml.etree.ElementTree as ET
import zipfile

import pytest

from claims_quality.dashboard import workbook
from claims_quality.tableau_extract import convert_dashboard


def fixture(directory, values):
    (directory / "Data").mkdir()
    with (directory / "Data/dashboard.csv").open("w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["panel", "label", "value", "unit"])
        writer.writerows(values)
    (directory / "Claims_Quality.twb").write_bytes(workbook([], 15905.27, 288))


def test_extract_round_trip_preserves_source_and_reads_packaged_values(tmp_path):
    hyper = pytest.importorskip("tableauhyperapi")
    rows = [
        ["Reconciliation", "Correct header total", "15905.27", "USD"],
        ["Monthly paid", "2024-11", "0", "USD"],
        ["Cohort PMPM", "Under 55", "55.461845238095236", "USD per member-month"],
    ]
    fixture(tmp_path, rows)
    original = (tmp_path / "Claims_Quality.twb").read_bytes()
    result = convert_dashboard(tmp_path)
    assert result["rows"] == 3
    assert result["extract_values_verified"] is True
    assert result["tableau_rendering_verified"] is False
    assert result["publishing_performed"] is False
    assert (tmp_path / "Claims_Quality.twb").read_bytes() == original
    with zipfile.ZipFile(tmp_path / "Claims_Quality_Public.twbx") as z:
        assert z.testzip() is None
        root = ET.fromstring(z.read("Claims_Quality_Public.twb"))
        assert root.get("source-build")
        ds = root.find("datasources/datasource")
        assert [e.tag for e in ds] == [
            "connection",
            "aliases",
            "column",
            "column",
            "column",
            "column",
            "extract",
        ]
        assert ds.find("extract").attrib == {"enabled": "true", "count": "-1", "units": "records"}
        connection = root.find("datasources/datasource/extract/connection")
        assert connection.get("class") == "hyper"
        packed = tmp_path / "roundtrip.hyper"
        packed.write_bytes(z.read(connection.get("dbname")))
    with hyper.HyperProcess(
        hyper.Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_dir": str(tmp_path)}
    ) as process:
        with hyper.Connection(process.endpoint, str(packed)) as con:
            actual = con.execute_list_query(
                'SELECT "label", "value", "unit" FROM "Extract"."Extract" ORDER BY "label"'
            )
    assert actual == [
        ["2024-11", 0.0, "USD"],
        ["Correct header total", 15905.27, "USD"],
        ["Under 55", 55.461845238095236, "USD per member-month"],
    ]


@pytest.mark.parametrize("value", ["nan", "inf", "-inf"])
def test_invalid_amount_does_not_publish_extract(tmp_path, value):
    fixture(tmp_path, [["Monthly paid", "2024-01", value, "USD"]])
    with pytest.raises(ValueError, match="finite"):
        convert_dashboard(tmp_path)
    assert not (tmp_path / "Claims_Quality_Public.twbx").exists()


def test_empty_input_does_not_publish_extract(tmp_path):
    fixture(tmp_path, [])
    with pytest.raises(ValueError, match="at least one"):
        convert_dashboard(tmp_path)
    assert not (tmp_path / "Claims_Quality_Public.twbx").exists()
