import pytest

from claims_quality.generate import generate
from claims_quality.model import read_dataset, write_dataset


@pytest.mark.parametrize(
    "text",
    [
        "",
        "unexpected_column\n",
        "record_id,member_id,member_id,birth_date\n",
        "record_id,member_id\n",
        "record_id,member_id,birth_date\nM0,MEM0\n",
        "record_id,member_id,birth_date\nM0,MEM0,1960-01-01,extra\n",
        "record_id,member_id,birth_date\nM0,,1960-01-01\n",
    ],
)
def test_malformed_csv_fails_even_without_rows(tmp_path, text):
    write_dataset(generate(), tmp_path)
    (tmp_path / "members.csv").write_text(text)
    with pytest.raises(ValueError, match="members"):
        read_dataset(tmp_path)


def test_schema_valid_empty_table_is_not_malformed_csv(tmp_path):
    data = generate()
    data["members"] = []
    write_dataset(data, tmp_path)
    assert read_dataset(tmp_path)["members"] == []


def test_integer_error_names_column_and_row(tmp_path):
    data = generate()
    data["claim_lines"][0]["units"] = "one"
    write_dataset(data, tmp_path)
    with pytest.raises(ValueError, match=r"claim_lines.units at CSV line 2"):
        read_dataset(tmp_path)
