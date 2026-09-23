import json

import pytest

from claims_quality import workflow


def test_one_command_outputs_and_repeatability(tmp_path):
    a = workflow.run(tmp_path / "a", seed=101, scenario="stress")
    b = workflow.run(tmp_path / "b", seed=101, scenario="stress")
    first = {str(p.relative_to(a)): p.read_bytes() for p in a.rglob("*") if p.is_file()}
    second = {str(p.relative_to(b)): p.read_bytes() for p in b.rglob("*") if p.is_file()}
    assert first == second
    result = json.loads((a / "evaluation.json").read_text())
    assert result["false_positives"] == result["false_negatives"] == []
    assert json.loads((a / "run.json").read_text())["evaluation_units"] == 17
    assert (a / "ISSUES.md").exists()
    assert not any("manifest" in p.name for p in (a / "dirty").iterdir())


def test_existing_run_is_never_overwritten(tmp_path):
    target = tmp_path / "existing"
    target.mkdir()
    (target / "important.txt").write_text("keep")
    with pytest.raises(ValueError, match="already exists"):
        workflow.run(target)
    assert (target / "important.txt").read_text() == "keep"


def test_failure_leaves_no_partial_run(tmp_path, monkeypatch):
    def fail(*args):
        raise ValueError("simulated detector failure")

    monkeypatch.setattr(workflow, "detect_directory", fail)
    with pytest.raises(ValueError, match="simulated"):
        workflow.run(tmp_path / "failed")
    assert list(tmp_path.iterdir()) == []


def test_review_groups_checks_and_explains_clean_result():
    base = dict(category="financial_reconciliation", table="claim_headers", record_id="H001")
    text = workflow.review_text(
        [
            dict(base, check_name="allocation"),
            dict(base, check_name="totals"),
            dict(base, check_name="totals"),
        ]
    )
    assert "2 distinct check-level flags" in text
    assert "**1 record/category issues**" in text
    assert "allocation, totals" in text
    assert "not confirmed fraud" in text
    assert "does not certify" in workflow.review_text([])


def test_review_rejects_unknown_categories():
    with pytest.raises(ValueError, match="Unknown"):
        workflow.review_text([dict(category="invented", table="members", record_id="M", check_name="x")])
