# Healthcare Claims Quality & Financial Reconciliation

**A claims reporting pipeline can produce financial totals that look plausible and are wrong.** This project builds the validation and reconciliation checks that catch that before the numbers reach a report.

**All data are synthetic.** No real members, providers, patient information, payer or employer data, or genuine healthcare coding are used.

## Key finding

On the baseline fixture, summing header payments after joining to claim lines reports **$37,011.02**, while the reconciled payment total is **$15,905.27**, an overstatement of **$21,105.75 (132.70%)**.

The difference is a reporting error caused by summing at the wrong grain, not savings or a production result.

## Dashboard

![Tableau dashboard showing claims financial reconciliation, monthly paid amounts, age-cohort paid per member-month, and validation results using controlled synthetic claims data.](docs/img/claims_dashboard.png)

*Tableau dashboard: financial reconciliation, monthly paid amounts, cohort PMPM and validation results.*

Every plotted value reconciles to the source results. Open `dashboard/Claims_Quality_Public.twbx` in Tableau Desktop or Tableau Public; the package carries its own extract, so no account or upload is needed. The [dashboard notes](dashboard/README.md) cover units, interactions and how to rebuild it.

## Why claims grain matters

A claim has one header carrying its payment, and one or more service lines beneath it. Joining headers to lines repeats the header's payment on every matching row, and summing after that join gives a total at the wrong grain.

Nothing errors. The query runs, the number is larger, and it looks reasonable. Unless someone reconciles it against another total, it ships.

## Reconciliation and quality checks

Three separate calculations agree on the correct total: summing at header grain, summing line payments, and aggregating lines to one row per claim before joining. Comparing a reported figure against those totals is what catches the error. `SUM(DISTINCT paid_cents)` is *not* a fix, because different claims can legitimately share a dollar amount.

DuckDB SQL checks also cover exact duplicate records, broken foreign keys and invalid date sequences. Records that fail a check are flagged for review and kept out of the reporting dataset.

## Data model

| Table | Declared business grain |
|---|---|
| `members` | One row per member_id |
| `providers` | One row per provider_id |
| `enrollment` | One row per enrollment_id |
| `claim_headers` | One row per claim_id |
| `claim_lines` | One row per claim_id + line_number |

Money is stored as integer cents so totals reconcile exactly. The fixture assumes allowed = paid + patient, billed ≥ allowed, non-negative amounts, and header totals that match their lines. An **exact duplicate** repeats every business field, including identifiers; different claim IDs with the same apparent service are treated as possible duplicate services for review.

See the [data dictionary](docs/DATA_DICTIONARY.md) and [metric definitions](docs/METRIC_DEFINITIONS.md).

## Methodology

The generator builds a clean baseline, then injects known defects into copies and records what it changed in a separate file. The SQL checks run on the raw tables without seeing that record, and their flags are scored against it afterwards. The test scenarios also include valid records that look like defects, to measure false positives as well as misses. Utilization and cohort metrics run only on the clean baseline.

Utilization uses enrollment denominators. Member-months count distinct enrolled member/calendar-month combinations, so overlapping coverage is not double-counted, and cohort rates are computed as summed numerator over summed denominator rather than an average of rates.

More detail: [architecture](docs/ARCHITECTURE.md), [technical notes](docs/TECHNICAL_NOTES.md), [validation protocol](docs/VALIDATION.md).

## Reproduce

Requires Python 3.11+.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
PYTHONPATH=src .venv/bin/python -m claims_quality run --seed 17 --scenario standard --out work/run-17
```

`run` generates the data, runs the checks and writes the flags, an `ISSUES.md` review queue, evaluation metrics and the join analysis. The [technical notes](docs/TECHNICAL_NOTES.md) describe each output, and the [architecture](docs/ARCHITECTURE.md) covers the other commands.

## Validation

Automated tests cover defect detection, claim relationships and foreign keys, financial reconciliation, utilization and cohort metrics, and the Tableau extract. Across 18 controlled scenarios and 4 seeds, the checks are measured on both missed defects and false alarms. Because the scenarios are generated, these scores do not estimate accuracy on real payer data.

Results: [validation summary](reports/VALIDATION_SUMMARY.md), [measured results](reports/RESULTS.md), [expanded evaluation](reports/expanded/EXPANDED_RESULTS.md), [executive brief](reports/EXECUTIVE_BRIEF.md).

## Limitations

The fixture is small and deterministic so that every expected result can be checked exactly; it says nothing about scale. November and December show zero claims because the generator limits service starts to the first 300 days of 2024, and apparent cohort, provider or monthly differences are likewise generator artifacts.

Claims are counted as claims, not visits, and payment lags are fixed rather than modeled. Real adjudication, payer rules, clinical validation and fraud detection are outside the scope of the fixture.

See [limitations](docs/LIMITATIONS.md) for the full list.
