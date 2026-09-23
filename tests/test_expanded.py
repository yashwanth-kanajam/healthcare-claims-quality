import pytest

from claims_quality.detect import detect, query
from claims_quality.evaluate import evaluate
from claims_quality.generate import generate, validate_clean
from claims_quality.scenarios import SCENARIOS, build_scenario


@pytest.mark.parametrize("seed", [17, 101, 202, 303])
@pytest.mark.parametrize("name", SCENARIOS)
def test_expanded_scenario(seed, name):
    clean = generate(seed)
    data, manifest = build_scenario(clean, name, seed)
    assert clean == generate(seed)
    assert (data, manifest) == build_scenario(clean, name, seed)
    if name.startswith("valid_"):
        validate_clean(data)
    result = evaluate(detect(data), manifest)
    assert result["false_positives"] == result["false_negatives"] == []


def test_overlap_counts_categories_not_checks():
    data, manifest = build_scenario(generate(), "overlapping_header_failures")
    assert len(manifest["expected_flags"]) == 3
    assert len({r["record_id"] for r in manifest["expected_flags"]}) == 1


def test_utilization_reconciles_and_keeps_zero_months():
    data = generate()
    monthly = query(data, "utilization.sql")
    cohorts = query(data, "cohorts.sql")
    assert len(monthly) == 12
    assert sum(r["member_months"] for r in monthly) == 24 * 12
    assert sum(r["claims"] for r in monthly) == 101
    assert sum(r["lines"] for r in monthly) == 197
    assert sum(r["paid_cents"] for r in monthly) == sum(h["paid_cents"] for h in data["claim_headers"])
    for field in ("claims", "member_months", "paid_cents"):
        assert sum(r[field] for r in cohorts) == sum(r[field] for r in monthly)
    assert monthly[-1]["claims"] == 0 and monthly[-1]["paid_per_member_month"] == 0


def test_denominators_use_coverage_not_claim_presence_or_duplicate_spans():
    data = generate()
    for e in data["enrollment"]:
        e["end_date"] = "2024-01-31"
    data["enrollment"].append(dict(data["enrollment"][0], record_id="EX", enrollment_id="ENRX"))
    rows = query(data, "utilization.sql")
    assert rows[0]["member_months"] == 24
    assert rows[1]["member_months"] == 0
    assert rows[1]["paid_per_member_month"] is None
    expected = [h for h in data["claim_headers"] if h["service_start"][:7] == "2024-01"]
    assert sum(r["claims"] for r in rows) == len(expected)
