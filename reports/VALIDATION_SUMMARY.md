# Validation summary

What was checked, the values it reconciles to, and what the synthetic fixture can and cannot establish.

## Financial reconciliation

Header paid and line paid totals each equal 1,590,527 cents (**$15,905.27**). Independently summing each header payment once per matching line reproduces the incorrect join at 3,701,102 cents (**$37,011.02**) — an overstatement of **$21,105.75 (132.70%)**.

Three independent paths agree on the reconciled total: summing at header grain, summing line payments, and aggregating lines to one row per claim before joining. That agreement is the control. `SUM(DISTINCT paid_cents)` is not a valid correction, because separate claims can legitimately share a dollar amount.

Monthly and cohort payments each total 1,590,527 cents, so the reporting views reconcile to the same baseline.

## Utilization and cohorts

Baseline fixture: 101 claims, 197 lines, 24 members, 288 enrolled member-months.

- Age 55 and over: $6,587.68 over 120 member-months = 54.897333333333336 PMPM
- Under 55: $9,317.59 over 168 member-months = 55.461845238095236 PMPM

Cohort rates are recomputed as summed numerator over summed denominator, never as an unweighted average of the two rates.

November and December each have 24 enrolled member-months, zero claims and zero paid spending. The generator limits service starts to the first 300 days of 2024. **This is a property of the fixture, not a seasonal pattern**, and must not be read as one.

## Defect detection

The expanded evaluation runs 18 controlled scenarios across 4 seeds. Detections were compared against an expected-label manifest held separately from the detector's inputs, with no unexpected or missed category or record flags.

True-positive units: exact duplicates 32, broken references 236, invalid date sequences 28, financial reconciliation 28. **These units are scenario-run, category and physical-row combinations** — not independent events, not patients, and not a measure of real-world detection accuracy.

The scenario set also includes valid lookalike cases that resemble defects but are legitimate, so the evaluation tests over-flagging as well as missed defects.

## Automated checks

Automated checks cover injected-defect detection, claim-level relationships and foreign-key integrity, financial reconciliation, utilization and cohort metrics, Tableau extract fidelity, and reproducible installation. A separate set of checks runs against the installed package outside the source checkout.

## Workbook integrity

The extract-backed workbook opens and renders all four panels. Every plotted numerical value reconciles to the validated source results. Axis titles identify their units, evaluation categories use readable names, and the synthetic-data disclaimer is retained on the dashboard.

The package has valid ZIP contents, relative data references, and an XML/CSV/Hyper payload identical to the adjacent repository files. The extract converter checks every Hyper row against the source CSV. Generated validation JSON does not assert native rendering automatically — that is confirmed by opening the workbook.

## Reproduction

A clean clone installed the package and its pinned Tableau dependency into a fresh virtual environment. All documented commands ran: generate, detect, report, run, review, expanded-report, dashboard and tableau-extract. Regenerated reports match the committed reports byte-for-byte, as do regenerated workbook XML, source CSV, and the monthly and cohort exports.

A scan of committed files and packaged content found no absolute machine paths and no credential patterns. All included data are generated synthetic fixtures and aggregate evaluation outputs.

## What this does not establish

These checks confirm the pipeline computes what it claims to compute, reproducibly, and that its controls catch the defects they were designed to catch.

They do not estimate real-world detection accuracy. The fixture is small and deterministic by design so that every expected result can be verified exactly; it is not a scale claim. No real patient, payer or employer data is involved at any point, and the dollar figures are synthetic demonstration values — not realized savings, recovered payments, or fraud findings.
