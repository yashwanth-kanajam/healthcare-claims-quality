# Executive brief — trust the reporting grain before interpreting spending

**Decision:** require grain-aware reconciliation and a source-record exception review before releasing claims payment KPIs.

On the controlled 2024 synthetic baseline, a header-to-line join reports **$37,011.02** when the correct total is **$15,905.27**. The error is **$21,105.75, or 132.70%**. Three correct calculations—header total, line total and a preaggregated join—agree. The error arises in analysis, even when the underlying records are internally consistent.

## Demonstration population and denominators

The generated baseline contains **24 members, 101 claims, 197 lines and 288 enrolled member-months**. Reconciled paid per member-month is **$55.23**; claims per 1,000 member-months are **350.69**. These are claims, not visits, and the rate is not annualized. Eligibility, monthly attribution and cohort definitions are documented in METRIC_DEFINITIONS.md.

## Quality evidence

The original evaluation tests four categories with controlled seeded defects. The expanded suite adds **72 scenario/seed runs across 18 named cases**, including dimension duplicates, orphan lines, absent provider cascades, birth/date conflicts, multi-category failures, missing lines and valid equal-date/multi-day cases. All observed flags match the separate expected labels in these cases: **32 duplicate, 236 foreign-key, 28 date and 28 financial true-positive units**, with zero false positives or misses. Many foreign-key units come from deleting one provider and evaluating its referencing records; event counts and affected-record counts are different.

No external clinical accuracy is established. The generator, mutations and expected labels are controlled by this project. Synthetic edge cases that pass structural checks are not asserted to be legitimate healthcare billing.

## Recommended operating workflow

1. Agree on source field meanings and business grain before joining.
2. Validate the input schema, source identifiers and reference relationships.
3. Reconcile all monetary columns before reporting; isolate quality flags for investigation.
4. Compute rates with explicit enrollment denominators and retain zero-activity periods.
5. Publish charts only after checking their totals against the SQL outputs.

No automatic record deletion, clinical decision or financial recovery is recommended from these fixtures. In a real engagement, obtain a representative source extract, independent labels and subject-matter review before assessing performance or changing business processes.

## What the dashboard does not establish

Observed cohort differences and zero-claim months are artifacts of synthetic generation. They do not establish unmet need, provider performance, patient behavior, seasonal demand or savings. The workbook was opened in Tableau Public 2026.2.2 and all four panels render; that rendering check is separate from the numerical reconciliation behind it.
