# Validation protocol

## Tested environment

Python 3.9.6, macOS arm64, DuckDB 1.4.3, pytest 8.4.2. Direct dependencies are pinned in `requirements-dev.txt`; `requirements-lock.txt` captures the full tested environment. Both source-checkout and installed-package workflows are supported; installed execution is tested outside the checkout. Other operating systems are unverified.

## Reproduce

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m claims_quality report --out work/reproduced-reports
```

Compare the generated `RESULTS.md` and `results.json` byte-for-byte with `reports/`. For an exact Python-3.9 dependency set, install `requirements-lock.txt` instead of the direct-dependency file. For a newer Python interpreter, the direct dependency file lets pip select compatible pytest transitive dependencies.

## Evaluation population and units

Four clean runs and twelve dirty runs: seeds 17/101/202/303, scenarios sparse/standard/stress. Seed 17 is development; the other seeds are declared value/placement variations using the same known mechanisms. This is internal controlled validation, not external or clinical validation.

Unit = scenario-run × category × table × physical record_id. Within a run, repeated checks in the same category collapse. Original and copied rows both count as exact-duplicate positives. The stress line defect produces two financial positives, line and header. Aggregate TP/FP/FN sum run-level counts; they do not deduplicate IDs across runs.

Precision = TP/(TP+FP), recall = TP/(TP+FN). A zero denominator produces null. No true-negative population, overall accuracy, confidence intervals, event-level score or clinical metric is reported. All thresholds are exact contract comparisons, not fitted statistical parameters.

## Evidence and independence

1. `validate_clean` checks clean tables using Python independently of SQL/manifest.
2. SQL detection finds zero flags on clean baseline variants.
3. Manifest labels describe known mutations and expected cascades; detector cannot accept the manifest.
4. A subprocess test detects from a CSV-only input directory with no manifest file.
5. Tests hand-count expected category totals and deliberately exercise false positives, false negatives and zero denominators in the evaluator.
6. SQL/financial results are checked against independently computed Python sums.
7. Focused rule tests cover each foreign key, every duplicate table, date checks and money-column reconciliation.

The modules share schema definitions and project authorship. “Independent” here refers to separate computational checks and label flow, not organizational independence or a protected execution environment.

## Release verification record

See `reports/VERIFICATION_0_2.md` for the latest checks; `reports/VERIFICATION.md` preserves the original release-1 evidence. `reports/results.json` records every run's category metrics, FP/FN tuples, row counts and analytics. `reports/RESULTS.md` is the business-facing summary generated from those values.

A report builder refuses to publish its passing summary if any run produces false positives or false negatives. A nonzero score difference should be investigated and documented, not removed from the denominator.
