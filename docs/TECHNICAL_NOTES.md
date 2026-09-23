# Technical notes

Design decisions behind the pipeline, and the assumptions each one rests on.

The question driving the work is narrow: **can the payment total be trusted, and which source records need investigation before it is published?** A large total is not a finding on its own — it may be an artifact of a join or of corrupt records. For seed 17, a naive header-to-line join produces $37,011.02 against a reconciled $15,905.27. Those are generated dollars, not costs or savings, and the conclusion they support is procedural: establish grain and reconciliation gates before publishing a figure.

## Row grain

A header is one claim. A line is one service entry inside a claim. A three-line claim has one header and three line rows. The composite line key is `(claim_id, line_number)`, because line 1 occurs in many claims.

Grain is declared before any payment is reported, which is what makes the rest of the pipeline checkable.

## Business keys versus physical keys

Two kinds of identity coexist:

- A business identifier answers *which member, claim or line is this supposed to represent?*
- `record_id` answers *which physical source row did we receive?*

A duplicated source row gets a new physical `record_id` so both occurrences stay traceable, while its business fields remain identical. Including `record_id` in a duplicate comparison would therefore hide every duplicate it was meant to find.

This also bounds what a primary key proves. A physical primary key enforces source-row identity only; multiple physical rows may still share a business key, so a physical key constraint is not evidence that `claim_id` is unique.

`model.py` holds the contract: `SCHEMA` maps tables to ordered columns and types, `KEYS` states the clean business grain, `MONEY` lists the four financial columns once so validation can loop over them without a copy-paste omission, and `CATEGORIES` fixes evaluation order. `write_dataset` writes columns in schema order; `read_dataset` checks columns and converts integer fields before loading. Dates stay ISO strings until DuckDB casts them to DATE. Ingestion rejects malformed data rather than inventing a default.

## Controlled synthetic design

`generate.py` uses a local `random.Random(seed)` object, so unrelated random calls elsewhere cannot shift the data. The same seed and pinned workflow reproduce the same records in the same order; another seed varies dates and amounts while preserving structure.

The baseline is 24 members, 6 providers, 24 enrollment spans, 96 ordinary claims plus 5 edge-case claims, and 197 lines. Ordinary claims cycle through one, two and three lines. For each line the generator creates an allowed amount, assigns a patient share, and calculates paid as the remainder; the header sums its lines. Financial consistency is therefore intentional rather than incidental — which is precisely what makes an injected one-cent break detectable.

Dates are deliberately simple: services occur in 2024, receipt three days later, payment ten days later. The resulting seven-day receipt-to-payment average is built in. It is not a discovery about payer operations.

`validate_clean` re-checks the baseline independently in Python — physical and business uniqueness, references, date order, coverage, positive units, money, and header/line sums. Independence matters because a bug shared by generation and SQL detection would otherwise look like agreement. These assertions are not a general healthcare validator, and they must run without Python's `-O` flag.

### Valid lookalikes

Five claims preserve cases that resemble defects but are not:

| Header | Case | Interpretation |
|---|---|---|
| H096 | Same apparent service as H000, new claim ID | Distinct record; possible service duplication unresolved |
| H097 | Different synthetic modifier | Not proof of legitimacy |
| H098 | Different units | Not proof of legitimacy; units are not a price formula |
| H099 | Different provider | Not proof of legitimacy |
| H100 | Zero payer payment, patient = allowed | Structurally reconciled under this contract |

The `SYN_*` labels are invented and carry no healthcare coding meaning. The distinction matters: calling every similar service "duplicate billing" overstates what the data supports.

## Defect injection without label leakage

`inject.py` deep-copies the baseline so the clean fixture survives. A second seeded generator selects distinct ordinary claims and reserves the five edge cases. Sparse, standard and stress scenarios inject one, two or three examples of each mechanism:

1. Copy a header with a new physical ID and unchanged business fields.
2. Replace a header's provider with a missing provider ID.
3. Set payment before receipt under the fixture's date contract.
4. Add 137 cents to a header's paid amount without changing its lines or patient amount.

Stress additionally adds 29 cents to one line's paid amount, breaking both the line allocation and its parent's reconciliation, so the manifest labels both records. One event can create several affected units.

The manifest — an event log plus expected row and category flags with reasons — is written under `ground_truth/`, not as columns on the raw data. The detector never imports that module, accepts a manifest argument, or reads that directory, and a separate-process test runs detection with only CSVs available.

This isolation does not make the evaluation externally independent: the same author designed both the fixture and the rules. What it does is prevent accidental label leakage at run time and keep the expected behavior auditable.

## Duplicate semantics

`duplicates.sql` uses `COUNT(*) OVER (PARTITION BY ...)`. Unlike `GROUP BY`, a window function keeps every original row while attaching its group count. The partition covers every business field and excludes only `record_id`, so a count above one means a repeated business record.

Every occurrence is flagged. Picking an arbitrary copy as the "good" one would conceal a real uncertainty about which physical row to retain. The rule does not flag the same identifier carrying differing attributes — that conflicting-key problem is explicitly deferred.

## Foreign-key checks

`checks.sql` asks `NOT EXISTS (...)` for each declared relationship — *does at least one matching parent exist?* An ordinary join could multiply results when a parent is duplicated; existence testing avoids that multiplication, though it does not certify parent uniqueness.

A missing member or provider flags the child row. A missing line-to-header reference flags the line, and the orphaned header may additionally lose its reconciled line total. That is a cascade, not necessarily a second independent source event — which is why a high foreign-key count is not a count of distinct source problems.

## Date contracts

The rules compare typed dates with `>` and `<`, so equality is valid. Header dates follow service_start <= service_end <= receipt <= payment. Line dates must be ordered and contained by their header. A linked member's birth date cannot follow service start.

These express the declared fixture semantics and nothing more. Before adapting them to a real feed, establish what "paid date" means for zero payments, denials, adjustments and multiple payment events. A plausible date rule copied without confirming source semantics produces false alarms.

## Financial controls

Row arithmetic tests nonnegative values, billed >= allowed, and allowed = paid + patient. The header reconciliation subquery groups lines by claim and sums each of the four amount columns; a LEFT JOIN retains headers with no lines, and `line_count IS NULL` catches those missing groups.

All amounts are integer cents — `1590527` cents is $15,905.27. Conversion to dollars happens only for display, never for equality checks.

`UNION ALL` combines check outputs. `detect.py` removes identical check tuples and sorts them so output is deterministic. Several distinct checks firing on one record stay useful for investigation even where they score as a single evaluation unit.

### Why the join overstates

Claim A with a $100 header and two lines paid $40 and $60 joins to:

| Joined row | Header paid | Line paid |
|---|---:|---:|
| A / line 1 | 100 | 40 |
| A / line 2 | 100 | 60 |

Summing header paid yields $200; summing line paid yields $100. The source data can be perfectly clean while the query is wrong — so record-level quality checks alone cannot certify a downstream calculation.

`analytics.sql` names the incorrect result, the header-grain result, the line-grain result and the preaggregated join result as CTEs, and returns them together with a Boolean comparison against the line ledger.

`SUM(DISTINCT header_paid)` is not a fix: two different claims may legitimately carry the same amount, and DISTINCT deduplicates values rather than claims. The fixture deliberately includes equal-dollar claims so that shortcut fails visibly. The preaggregated join assumes unique headers and can overcount if dirty headers repeat, which is why the demonstration analytics run only on the validated baseline.

## Denominator choices

`utilization.sql` builds a 12-month calendar and tests enrollment overlap with EXISTS, counting each member-month once including months with no claims. `cohorts.sql` applies the same denominator and eligibility rules across age groups.

A ratio must combine underlying numerators and denominators. Adding group PMPM values, or averaging them unweighted, is wrong. The baseline's 288 member-months are 24 members across 12 covered months, and $15,905.27 over 288 is about $55.23 per member-month.

`scenarios.py` extends the fixture family beyond header defects; each named scenario starts from a fresh baseline and records expected effects before detection. A single header can carry three categories while counting once per category. `expanded.py` records discrepancies rather than omitting failing runs from the report.

## Evaluation boundaries

`evaluate.py` converts flags into sets of `(category, table, record_id)` tuples. Set intersection gives true positives, actual minus expected gives false positives, and expected minus actual gives false negatives.

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
```

A zero denominator yields `None` in Python and `null` in JSON — it does not become a perfect score. Clean runs have no positives and no predictions, so both metrics are undefined; their meaningful result is zero flags against independently valid data.

Two financial checks on one header count once within that category, though one row can contribute to two different categories. Reports pool scenario-run units: the same textual record ID appearing in two runs is two separate observations, not one deduplicated record.

Seed 17 is the development seed. Seeds 101, 202 and 303 vary values and placement across the same sparse, standard and stress mechanisms. They are not unseen mechanisms, and they were inspected during validation, so they are not an unbiased external test set. The measured perfect scores show only that these controlled fixtures behave as specified.

The test suite states falsifiable claims rather than demonstrating correctness: repeatability and immutability, clean-seed invariants, independently calculated Python totals agreeing with SQL, a twelve-combination evaluation grid with hand-counted category totals, both copies of every duplicate flagged, focused mutations for each foreign-key and date rule, one-cent reconciliation breaks at both grains, edge cases remaining valid, deliberate evaluator failure cases including undefined denominators, and a CSV-only subprocess run that needs no manifest. A passing suite is evidence about those assertions, not proof of an absence of bugs; `LIMITATIONS.md` covers which input families remain untested.

## Workflow and packaging

`claims-quality run --seed 17 --scenario standard --out work/run-17` performs generation, clean validation, injection, CSV detection, scoring and review output. Failure leaves no final directory, so a folder at the requested path means every stage succeeded — against the controlled fixture, which is not a claim about real-world data.

`ISSUES.md` is the entry point: it groups multiple checks within one record and category and attaches an investigation action. `flags.json` holds granular check evidence, `evaluation.json` the measured comparisons, and `run.json` the seed, scenario and row counts. Ground truth stays in its own directory, and the issue report does not read it.

`workflow.py` uses `TemporaryDirectory` as a context manager so cleanup happens even when a detector raises. Only after validation does `rename` move the staged result into place, and an existing directory is refused rather than overwritten.

The SQL lives in the package's `sql` folder, included as package data, with a `claims-quality` entry point. Testing the installed wheel from a different working directory catches a common packaging bug: code that works in the repository because its SQL happens to be nearby, but fails once installed because those files were never included.

## Dashboard handoff

`dashboard.py` runs the SQL and exports a self-contained Tableau package alongside the monthly and cohort CSVs. Each view filters a separate metric panel so dollars, PMPM values and evaluation counts cannot be added together.

The executive brief states what a stakeholder should do differently: verify grain and reconcile before interpreting the numbers. Workbook rendering was verified separately from numerical correctness — passing SQL checks say nothing about whether a workbook opens.
