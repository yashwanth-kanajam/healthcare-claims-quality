# Expanded controlled evaluation

72 scenario/seed runs across 18 named mechanisms and edge cases. 0 runs disagree with expected labels.

Labels describe known mutations and their downstream effects; SQL never receives the labels. Evaluation unit is scenario-run/category/table/physical record ID. Multiple checks in one category collapse; deleted parent rows are not themselves flagged when absent. Their referring records are evaluated.

| Category | TP | FP | FN | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| exact_duplicate | 32 | 0 | 0 | 1.0 | 1.0 |
| broken_foreign_key | 236 | 0 | 0 | 1.0 | 1.0 |
| invalid_date_sequence | 28 | 0 | 0 | 1.0 | 1.0 |
| financial_reconciliation | 28 | 0 | 0 | 1.0 | 1.0 |

| Scenario | Runs | Expected units across seeds | False positives | Missed units |
|---|---:|---:|---:|---:|
| duplicate_member | 4 | 8 | 0 | 0 |
| duplicate_provider | 4 | 8 | 0 | 0 |
| duplicate_enrollment | 4 | 8 | 0 | 0 |
| duplicate_line | 4 | 12 | 0 | 0 |
| orphan_enrollment | 4 | 4 | 0 | 0 |
| orphan_member | 4 | 4 | 0 | 0 |
| orphan_line | 4 | 8 | 0 | 0 |
| orphan_line_provider | 4 | 4 | 0 | 0 |
| enrollment_reversed | 4 | 4 | 0 | 0 |
| line_reversed | 4 | 4 | 0 | 0 |
| member_born_after_service | 4 | 16 | 0 | 0 |
| missing_claim_lines | 4 | 4 | 0 | 0 |
| negative_header_payment | 4 | 4 | 0 | 0 |
| line_billed_below_allowed | 4 | 8 | 0 | 0 |
| overlapping_header_failures | 4 | 12 | 0 | 0 |
| missing_provider_cascade | 4 | 216 | 0 | 0 |
| valid_equal_dates | 4 | 0 | 0 | 0 |
| valid_multiday_claim | 4 | 0 | 0 | 0 |

Full discrepant tuples and per-category denominators are preserved in expanded-results.json. Undefined precision/recall is null, including valid-only scenarios. Perfect controlled scores are not external healthcare accuracy. These scenarios broaden tested mechanisms within the same four categories; they do not validate clinical legitimacy or real payer formats.

The missing-provider and birth-date cases label known referencing children explicitly. The overlap case counts one header in three categories. The duplicate-line, orphan-line and line-billed cases count expected header reconciliation consequences. Cases are evaluated independently rather than mixed into one ambiguous master dataset.
