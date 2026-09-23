# Architecture and rule design

## Flow and separation

```text
generate(seed) --> clean tables --> independent Python invariants
                        |
                 inject(seed, scenario) --> dirty raw tables
                        |                        |
                        v                        v
                  truth manifest           SQL detector
                        |                        |
                        +----> evaluator <-------+
                                  |
                            measured reports
```

The injector describes known mutations and their expected row/category consequences. It does not call detection. The detector imports the table contract and DuckDB only, opens only the five named raw CSV files when called from the CLI, and executes two SQL files. No scenario ID, random seed, truth bit or expected label is a raw-data column. The evaluator is downstream and sees already-computed flags. This is separation by API/module/file design, not an OS security sandbox against a malicious developer.

SQL files are bundled under `src/claims_quality/sql/` so installed execution does not depend on the caller’s working directory.

## Files and responsibilities

| File | Responsibility |
|---|---|
| model.py | Single column/type/key contract; deterministic CSV read/write |
| generate.py | Repeatable clean data and independent non-SQL invariants |
| inject.py | Deep-copy mutation, injection-event log and expected flags |
| detect.py | Typed in-memory staging, parameterized inserts, SQL execution |
| evaluate.py | Set-based scoring at the declared evaluation unit |
| report.py | Fixed evaluation grid and deterministic readable/JSON outputs |
| __main__.py | generate, detect, report, run and review command routing |
| workflow.py | Complete isolated synthetic run and label-free grouped issue report |
| duplicates.sql | Exact repeated business rows for all five tables |
| checks.sql | Foreign-key, date and financial checks |
| analytics.sql | Deliberately wrong join and three correct payment totals |
| business_summary.sql | Clean provider-group claim counts and payments |
| test_pipeline.py | Independent oracles and adversarial/edge fixtures |

The database is fresh and in-memory per call, preventing state leaking between scenarios. Connections close in `finally` blocks. Ingested values are parameterized; table/column names come from an internal fixed schema. Foreign-key constraints are not physically enforced in staging because observing violations is the purpose.

## Four categories

1. **exact_duplicate**: a window COUNT partitions on all business fields. Every record in a partition with count > 1 is flagged. Two rows with the same declared key but a changed attribute are a conflicting-key case, not an exact duplicate. They are deferred, explicitly tested as outside this rule.
2. **broken_foreign_key**: NOT EXISTS checks enrollment → member, header → member/provider and line → header/provider. An absent parent is flagged on the referring row. No inference about patient eligibility or provider credentialing is made.
3. **invalid_date_sequence**: enrollment start <= end; header service_start <= service_end <= receipt <= payment; member birth <= linked service start; line start <= end and within header bounds. Equal dates are allowed.
4. **financial_reconciliation**: nonnegative money, billed >= allowed, allowed = paid + patient, and all four header amounts match summed lines. Missing lines fail explicitly.

## Overlaps and cascades

Output is check-level: `category`, `table`, `record_id`, `check_name`. The evaluator collapses repeated checks within one category and record. A header payment mutation can violate both allocation and line totals yet counts once in financial precision/recall. A changed line payment creates two financial units: the line's allocation and the parent's total. A duplicated line produces exact-duplicate positives for both line occurrences and a financial mismatch on the parent. A missing line-to-header key flags the orphan and can leave the original header unreconciled. Tests cover these cascades; event counts must not be mistaken for affected-record counts.

The published injection grid isolates four header-level mutations on different claims, then adds one explicit line-to-header cascade in stress. It is deliberately simple enough to audit. Additional tests mutate dimension and line records without claiming a larger held-out evaluation population.

## Service lookalikes

H096 repeats H000's apparent service using a new claim ID. H097 changes an illustrative modifier, H098 changes units, H099 changes provider, H100 has zero payer payment with a reconciled allocation. They are not exact-record duplicates. The first four may still deserve real-world service review; even the differences do not prove legitimacy. Release 1 does not implement a potential-service-duplicate scoring algorithm and reports no performance for one.

## Why the join overcounts

One header payment attached to three lines appears three times after a join. SUM(header.paid) then counts it three times. Correct alternatives: sum headers directly, sum line payments directly, or aggregate lines by claim before joining to unique clean headers. All rely on known grain and validated source relationships. Dirty duplicate headers can break even the preaggregated join; the demonstration intentionally runs only on the verified clean baseline. SUM(DISTINCT amount) drops valid equal-dollar claims and is explicitly counterexample-tested.

## Version 0.2 workflow safety

`run` generates a baseline, validates it independently and through SQL, then injects and detects dirty data from CSV. Labels are passed only to the downstream evaluator and are saved after detection. A temporary sibling directory holds all files until successful completion. Existing output directories are rejected; a failed run removes its temporary files and leaves no final directory. This is local file publication, not a GitHub upload.

`review` accepts saved flags, groups check names by category/table/record_id, and writes investigation guidance. It does not infer labels, rank clinical legitimacy or estimate recovered money. CSV ingestion validates headers before reading rows, rejects duplicate/missing columns and malformed row widths, and names invalid integer fields in its error messages. A header-only table with the correct schema remains valid input; missing parents will be assessed by the relationship checks.
