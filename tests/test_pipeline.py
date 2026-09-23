import copy
import json
import subprocess
import sys

import pytest

from claims_quality.detect import detect, query
from claims_quality.evaluate import evaluate, key
from claims_quality.generate import generate, validate_clean
from claims_quality.inject import inject
from claims_quality.model import MONEY, SCHEMA, write_dataset


@pytest.fixture(scope="module")
def clean():
    return generate(17)


def test_repeatability_and_seed_variation():
    assert generate(17) == generate(17)
    assert generate(17) != generate(18)
    data = generate(17)
    assert inject(data, 17) == inject(data, 17)
    assert data == generate(17)  # injection never mutates the baseline


@pytest.mark.parametrize("seed", [17, 101, 202, 303])
def test_clean_invariants_and_no_flags(seed):
    data = generate(seed)
    validate_clean(data)
    assert detect(data) == []


def test_money_and_grain(clean):
    for field in MONEY:
        assert sum(h[field] for h in clean["claim_headers"]) == sum(ln[field] for ln in clean["claim_lines"])
    a = query(clean, "analytics.sql")[0]
    truth = sum(h["paid_cents"] for h in clean["claim_headers"])
    wrong = sum(
        h["paid_cents"] * sum(ln["claim_id"] == h["claim_id"] for ln in clean["claim_lines"])
        for h in clean["claim_headers"]
    )
    assert (
        a["correct_header_paid_cents"]
        == a["correct_line_paid_cents"]
        == a["correct_preaggregated_join_paid_cents"]
        == truth
    )
    assert a["incorrect_join_paid_cents"] == wrong > truth
    assert a["overstatement_cents"] == wrong - truth
    assert a["reconciliation_catches_error"] is True
    summary = query(clean, "business_summary.sql")
    assert sum(r["paid_cents"] for r in summary) == truth
    assert sum(r["claim_count"] for r in summary) == len(clean["claim_headers"])


@pytest.mark.parametrize("seed", [17, 101, 202, 303])
@pytest.mark.parametrize("scenario", ["sparse", "standard", "stress"])
def test_evaluation_grid(seed, scenario):
    dirty, manifest = inject(generate(seed), seed, scenario)
    result = evaluate(detect(dirty), manifest)
    assert result["false_positives"] == []
    assert result["false_negatives"] == []
    assert all(m["precision"] == m["recall"] == 1.0 for m in result["metrics"])
    # Hand-counted unit oracle, not derived by re-running detection.
    factor = {"sparse": 1, "standard": 2, "stress": 3}[scenario]
    assert [m["tp"] for m in result["metrics"]] == [
        factor * 2,
        factor,
        factor,
        factor + (2 if scenario == "stress" else 0),
    ]


@pytest.mark.parametrize("table", list(SCHEMA))
def test_exact_duplicates_all_tables(clean, table):
    data = copy.deepcopy(clean)
    source = data[table][0]
    duplicate = copy.deepcopy(source)
    duplicate["record_id"] += "_COPY"
    data[table].append(duplicate)
    actual = {key(r) for r in detect(data)}
    assert {k for k in actual if k[0] == "exact_duplicate"} == {
        ("exact_duplicate", table, source["record_id"]),
        ("exact_duplicate", table, duplicate["record_id"]),
    }
    if table == "claim_lines":
        assert ("financial_reconciliation", "claim_headers", "H000") in actual
    else:
        assert len(actual) == 2


def test_same_identifier_changed_attribute_is_not_exact_duplicate(clean):
    data = copy.deepcopy(clean)
    duplicate = dict(data["providers"][0], record_id="PX", provider_type="SYN_OTHER")
    data["providers"].append(duplicate)
    assert detect(data) == []  # conflicting-key profiling is explicitly outside these four checks


def test_valid_lookalikes_not_called_exact_duplicates(clean):
    a = clean["claim_headers"][0]
    b = clean["claim_headers"][96]
    assert a["claim_id"] != b["claim_id"]
    assert {k: v for k, v in a.items() if k not in ("claim_id", "record_id")} == {
        k: v for k, v in b.items() if k not in ("claim_id", "record_id")
    }
    assert detect(clean) == []
    assert clean["claim_headers"][100]["paid_cents"] == 0
    assert clean["claim_headers"][0]["paid_cents"] > 0
    # A repeated dollar amount across distinct claims shows why SUM(DISTINCT amount) is not a repair.
    assert sum(h["paid_cents"] for h in clean["claim_headers"]) > sum(
        {h["paid_cents"] for h in clean["claim_headers"]}
    )


@pytest.mark.parametrize(
    "table,field,check",
    [
        ("enrollment", "member_id", "enrollment_member_exists"),
        ("claim_headers", "member_id", "header_member_exists"),
        ("claim_headers", "provider_id", "header_provider_exists"),
        ("claim_lines", "claim_id", "line_header_exists"),
        ("claim_lines", "provider_id", "line_provider_exists"),
    ],
)
def test_each_foreign_key(clean, table, field, check):
    data = copy.deepcopy(clean)
    data[table][0][field] = "MISSING"
    flags = detect(data)
    assert any(r["record_id"] == data[table][0]["record_id"] and r["check_name"] == check for r in flags)
    if table == "claim_lines" and field == "claim_id":
        assert any(r["record_id"] == "H000" and r["check_name"] == "header_line_totals" for r in flags)


@pytest.mark.parametrize(
    "table,field,value,check",
    [
        ("enrollment", "end_date", "2023-12-31", "enrollment_dates_ordered"),
        ("claim_headers", "service_start", "2025-01-01", "header_dates_ordered"),
        ("claim_headers", "received_date", "2023-01-01", "header_dates_ordered"),
        ("claim_headers", "paid_date", "2023-01-01", "header_dates_ordered"),
        ("members", "birth_date", "2025-01-01", "service_not_before_birth"),
        ("claim_lines", "service_end", "2023-01-01", "line_dates_ordered"),
        ("claim_lines", "service_start", "2023-01-01", "line_within_header_dates"),
    ],
)
def test_date_rules(clean, table, field, value, check):
    data = copy.deepcopy(clean)
    data[table][0][field] = value
    assert check in {r["check_name"] for r in detect(data)}


@pytest.mark.parametrize("table", ["claim_headers", "claim_lines"])
@pytest.mark.parametrize("field", MONEY)
def test_each_money_column_reconciles(clean, table, field):
    data = copy.deepcopy(clean)
    data[table][0][field] += 1
    assert any(r["record_id"] == "H000" and r["check_name"] == "header_line_totals" for r in detect(data))


def test_boundary_equal_dates_allowed(clean):
    data = copy.deepcopy(clean)
    h = data["claim_headers"][0]
    h["received_date"] = h["paid_date"] = h["service_end"]
    assert detect(data) == []


def test_no_lines_is_reconciliation_failure(clean):
    data = copy.deepcopy(clean)
    data["claim_lines"] = [ln for ln in data["claim_lines"] if ln["claim_id"] != "CLM000"]
    assert {key(r) for r in detect(data)} == {("financial_reconciliation", "claim_headers", "H000")}


def test_evaluator_handles_misses_false_alarms_and_zero_denominators():
    row = dict(category="exact_duplicate", table="members", record_id="M")
    assert evaluate([], {"expected_flags": []})["metrics"][0] == dict(
        category="exact_duplicate", tp=0, fp=0, fn=0, precision=None, recall=None
    )
    missed = evaluate([], {"expected_flags": [row]})["metrics"][0]
    assert missed["fn"] == 1 and missed["precision"] is None and missed["recall"] == 0
    alarm = evaluate([row, dict(row, check_name="second")], {"expected_flags": []})["metrics"][0]
    assert alarm["fp"] == 1 and alarm["precision"] == 0 and alarm["recall"] is None


def test_detector_process_needs_only_raw_csvs(clean, tmp_path):
    dirty, manifest = inject(clean)
    write_dataset(dirty, tmp_path / "raw")
    output = tmp_path / "flags.json"
    # Deliberately no manifest on disk. Detection runs in a separate process.
    subprocess.run(
        [
            sys.executable,
            "-m",
            "claims_quality",
            "detect",
            "--data",
            str(tmp_path / "raw"),
            "--out",
            str(output),
        ],
        check=True,
        env=__import__("os").environ.copy() | {"PYTHONPATH": "src"},
        capture_output=True,
    )
    assert evaluate(json.loads(output.read_text()), manifest)["false_negatives"] == []
    assert evaluate(json.loads(output.read_text()), manifest)["false_positives"] == []


def test_detection_is_invariant_to_physical_id_names(clean):
    data, manifest = inject(clean, scenario="stress")
    renames = {}
    for table, rows in data.items():
        for i, row in enumerate(rows):
            new_id = f"source-{i:06}"
            renames[(table, row["record_id"])] = new_id
            row["record_id"] = new_id
    for row in manifest["expected_flags"]:
        row["record_id"] = renames[(row["table"], row["record_id"])]
    result = evaluate(detect(data), manifest)
    assert result["false_positives"] == result["false_negatives"] == []


@pytest.mark.parametrize("table", ["claim_headers", "claim_lines"])
def test_negative_money_is_rejected_even_when_allocation_balances(clean, table):
    data = copy.deepcopy(clean)
    row = data[table][0]
    row["paid_cents"] = -1
    row["patient_cents"] = row["allowed_cents"] + 1
    check = "header_amount_contract" if table == "claim_headers" else "line_amount_contract"
    assert any(r["record_id"] == row["record_id"] and r["check_name"] == check for r in detect(data))
