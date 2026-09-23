# Analyst refresher: build, question, explain

This walkthrough assumes you have used SQL and Python before but want to rebuild fluency. Work through one section at a time. The aim is to explain why each choice exists, then verify it yourself. It is not a healthcare billing tutorial.

## 1. Start with a question that has a decision attached

The business question is: **Can an analyst trust the payment total, and which source records need investigation before publishing it?** A large total is not automatically a business finding. It may be an artifact of joins or corrupt records.

Success here means reproducible data, explicit assumptions, correct arithmetic at the intended grain, actionable record-level flags, and evidence that checks detect what they claim. A polished chart would not fix a wrong denominator or repeated payment. That is why release 1 focuses on the data and reasoning.

Read `reports/RESULTS.md`. For seed 17, a naive join produces $37,011.02 against a reconciled $15,905.27. These are generated dollars, not actual costs or savings. Your practical recommendation is to establish grain and reconciliation gates, not to claim a recovery opportunity.

## 2. Refresh your environment skills

A virtual environment isolates this project's Python libraries from other work. `python -m pip` invokes pip through the chosen Python interpreter; it reduces confusion from accidentally installing into another environment. The two direct dependencies are DuckDB, the local SQL engine, and pytest, the test runner.

Follow README's commands. `PYTHONPATH=src` tells Python where the source package lives. `python -m claims_quality` executes `__main__.py`. Its argument parser selects a command and validates required options. The code deliberately uses small modules rather than one long notebook so tests can import functions directly.

Generated artifacts go under ignored `work/`. Committed reports go under `reports/`. Re-running a command with the same output path overwrites those generated artifacts; keep exploratory runs in separate folders if you want to compare them. No command writes to the remote repository.

**Checkpoint:** after generation, you should see five CSVs in `work/demo/clean`, five in `work/demo/dirty`, and one manifest in `work/demo/ground_truth`. Do not hand the manifest to detection.

## 3. Understand row grain before writing SQL

A header is one claim. A line is one service entry inside a claim. A three-line claim has one header and three line rows. The composite line key is `(claim_id, line_number)`, because line 1 occurs in many claims.

There are two kinds of identity:

- A business identifier answers “which member/claim/line is this supposed to represent?”
- `record_id` answers “which physical source row did we receive?”

A duplicated source row gets a new physical `record_id` so both occurrences remain traceable. All its business fields remain identical. If you included `record_id` in duplicate comparison, you would never see that duplicate.

Read `model.py` alongside `DATA_DICTIONARY.md`. `SCHEMA` is an ordered mapping of table names to column names/types. `KEYS` states clean business grain. `MONEY` lists four financial columns once so validation can loop over them without a copy/paste omission. `CATEGORIES` fixes evaluation order.

`write_dataset` writes columns in schema order using Python's CSV library. `read_dataset` checks the columns and converts integer fields before loading. Dates remain ISO strings until DuckDB casts them into DATE columns. Ingestion rejects malformed data instead of inventing a default.

**Exercise:** explain why adding a physical primary key does not prove `claim_id` is unique. Answer: it enforces source-row identity only; multiple physical rows may share a business key.

## 4. Read the generator as a data contract

`generate.py` creates a local `random.Random(seed)` object. Local randomness avoids unrelated random calls elsewhere changing your data. The same seed and pinned workflow produce the same records and ordering. Another seed changes dates and monetary values while preserving structure.

The baseline has 24 members, 6 providers, 24 enrollment spans, 96 ordinary claims plus 5 edge-case claims, and 197 total lines. Ordinary claims cycle through one, two and three lines. For each line, the generator creates an allowed amount, assigns an illustrative patient share, and calculates paid as the remainder. The header sums the line values. This design makes financial consistency intentional.

Dates are deliberately simple: services occur in 2024; receipt is three days later and payment ten days later. The seven-day receipt-to-payment average is therefore built in. It is not a discovery about payer operations.

`validate_clean` then checks the baseline independently in Python: physical/business uniqueness, references, date order, coverage, positive units, money and header/line sums. Independence matters because a bug shared by generation and SQL detection could otherwise appear correct. These assertions are not a universal healthcare validator and must run without Python's `-O` option.

**Exercise:** change only a generated header's paid cents by 1 in a scratch copy. Which independent baseline assertion should fail? Both the aggregate relationship and the paid-plus-patient allocation can fail; which appears first depends on assertion order.

## 5. Treat similar services with skepticism

Five additional claims preserve edge cases:

| Header | Deliberate case | Interpretation |
|---|---|---|
| H096 | Same apparent service as H000, new claim ID | Distinct record; possible service duplication is unresolved |
| H097 | Different synthetic modifier | Not proof of legitimacy |
| H098 | Different units | Not proof of legitimacy; units are not a price formula |
| H099 | Different provider | Not proof of legitimacy |
| H100 | Zero payer payment, patient = allowed | Structurally reconciled under this contract |

The `SYN_*` labels are invented. Do not explain their meaning using actual healthcare coding rules. This distinction is valuable in an interview: precision in definitions is more credible than calling every similar service “duplicate billing.”

## 6. Inject defects without leaking the answers

`inject.py` makes a deep copy so the clean baseline survives. A second seeded generator chooses distinct ordinary claims; the five edge cases are reserved. Sparse, standard and stress scenarios inject one, two or three examples of each primary mechanism.

The mechanisms are:

1. Copy a header with a new physical ID and unchanged business fields.
2. Replace a header's provider with a missing provider ID.
3. Set payment before receipt under the fixture's date contract.
4. Add 137 cents to a header's paid amount without changing its lines or patient amount.

Stress also adds 29 cents to one line's paid amount. That breaks the line allocation and its parent's reconciliation, so the manifest labels both records. One event can create multiple affected units.

The manifest has an event log and expected row/category flags with reasons. It is written under `ground_truth/`, not added as columns to raw data. The detector never imports this module, accepts a manifest argument or reads that directory. A separate-process test runs detection with only CSV files available in its input folder.

This does not make the evaluation externally independent: the same project author designed the fixture and rules. It prevents accidental label leakage during execution and makes the expected behavior auditable.

## 7. Read the SQL in four passes

### Exact duplicates: a window function

`duplicates.sql` uses `COUNT(*) OVER (PARTITION BY ...)`. Unlike `GROUP BY`, a window function retains every original row while attaching a group count. The partition includes every business field and excludes only physical `record_id`. A count above one means repeated business records.

All occurrences are flagged. Picking an arbitrary original as “good” would hide uncertainty about which physical copy to retain. This rule does not flag the same identifier with differing attributes; that is an explicitly deferred conflicting-key problem.

### Foreign keys: existence without multiplication

`checks.sql` asks `NOT EXISTS (...)` for each declared relationship. Think “does at least one matching parent exist?” An ordinary join could multiply results if a parent is duplicated. Existence avoids that multiplication; it does not certify parent uniqueness.

A missing member/provider flags the child row. A missing line-to-header reference flags the line, and the former header may additionally lose its reconciled line total. That is a cascade, not necessarily a second independent source event.

### Dates: domain assumptions must be visible

The rules compare typed dates with `>` and `<`, so equality is valid. Header dates follow service_start <= service_end <= receipt <= payment. Line dates must be ordered and contained by the header. A linked member's birth cannot follow service start.

These rules express the declared fixture semantics. Before adapting them to a real feed, ask what “paid date” means for zero payments, denials, adjustments and multiple payment events. Copying a plausible date rule without confirming source semantics can produce false alarms.

### Money: row arithmetic and aggregate reconciliation

Line/header arithmetic tests nonnegative values, billed >= allowed, and allowed = paid + patient. The header reconciliation subquery groups lines by claim and sums each of the four amount columns. A LEFT JOIN retains headers even when lines are absent; `line_count IS NULL` catches those missing groups.

All amounts are integer cents. `1590527` cents represents $15,905.27. Display formatting converts to dollars only in the report; it is not used for equality checks.

`UNION ALL` combines check outputs. `detect.py` removes identical check tuples and sorts them, making output deterministic. Multiple different checks remain useful for investigation even when they score as one evaluation unit.

## 8. Explain the double-counting trap with a tiny example

Imagine claim A has a $100 header and two lines paid $40 and $60:

| Joined row | Header paid | Line paid |
|---|---:|---:|
| A / line 1 | 100 | 40 |
| A / line 2 | 100 | 60 |

Summing header paid yields $200; summing line paid yields $100. The source data can be perfectly clean while the analytical query is wrong. Record-quality checks alone cannot certify every downstream calculation.

`analytics.sql` uses common table expressions (CTEs) to name the incorrect result, header-grain result, line-grain result and preaggregated join result. The final SELECT returns all results together and a Boolean comparison with the line ledger.

Why not `SUM(DISTINCT header_paid)`? Because two different claims may both legitimately have the same dollar amount. DISTINCT deduplicates values, not claims. The test fixture includes equal-dollar claims to make that shortcut fail.

The preaggregated join also assumes unique headers. If dirty headers repeat, it can overcount again. This is why demonstration analytics run only on the validated baseline.

## 9. Measure detection honestly

`evaluate.py` converts flags into sets of `(category, table, record_id)` tuples. Set intersection gives true positives. Actual minus expected gives false positives. Expected minus actual gives false negatives.

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
```

A zero denominator yields `None` in Python and `null` in JSON. It does not become a perfect score. Clean runs have no positives or predictions, so both metrics are undefined; their useful result is zero flags against independently valid data.

Two financial checks on the same header count once within that category. One row can still contribute to two different categories. Reports pool scenario-run units: the same textual record ID in two runs represents two separate evaluated observations, not one cross-run deduplicated record.

Seed 17 is development. Seeds 101, 202 and 303 provide held-out value/placement variation across the same sparse/standard/stress mechanisms. They are not unseen mechanisms and were still inspected during validation. Avoid saying “unbiased external test set.” The measured perfect scores only show that these controlled fixtures behave as specified.

## 10. Read tests as falsifiable claims

`tests/test_pipeline.py` contains assertions that can fail for meaningful reasons:

- Repeatability and immutability: seeds reproduce results and injection leaves clean input unchanged.
- Clean seeds: independent invariants pass and SQL emits zero flags.
- Money and joins: independently calculated Python totals agree with SQL; the wrong join really overstates.
- Evaluation grid: twelve dirty combinations match truth, with hand-counted category totals.
- Every duplicate table: both copies are flagged, with the line-to-header financial cascade checked.
- Each foreign key and date rule: focused mutations exercise their specific checks.
- Each money column at both grains: reconciliation catches one-cent changes.
- Edge cases: equal dates, same-service different-ID records, zero payment and repeated amounts remain valid under the contract.
- Evaluator failure cases: deliberately missed positives and false alarms produce the expected scores, including undefined denominators.
- CSV-only subprocess: detection needs no manifest and round-trips the generated data.

A passing test suite is evidence about these assertions, not proof there are no bugs. Ask which untested input families remain; see LIMITATIONS.md.

## 11. Turn the evidence into an interview narrative

Use this as a structure, adapting the wording to your own understanding:

> I built a reproducible synthetic claims-quality case study using Python and DuckDB SQL. I declared header and line grain before reporting payments. A naive header-to-line join overstated the generated payment total by $21,105.75, and three corrected calculations reconciled to $15,905.27. I separated defect labels from detection, tested valid lookalikes and cascades, and measured precision/recall across controlled scenarios. Those results validate the fixtures, not real payer accuracy. My next step with real data would be to agree on source semantics and obtain independently reviewed examples.

Be ready to show the SQL, explain a failed test, and distinguish a rule's assumptions from healthcare facts. Do not claim deployment, business savings, clinical expertise or employer sponsorship that did not happen.

## 12. Practice extensions without inflating release 1

In a scratch branch, try a same-key conflicting provider attribute and observe that the exact-duplicate detector does not flag it. Explain why before proposing a fifth category. Then change a line's claim ID and trace the orphan plus parent financial cascade. Finally, design an independent labeled scenario with a new mechanism and decide the unit of evaluation before writing its detector.

These are learning exercises, not included production capabilities. Prefer one well-defined rule with a counterexample over a long list of vaguely named checks.

## 13. Run and inspect the completed workflow (version 0.2)

After installation, `claims-quality run --seed 17 --scenario standard --out work/run-17` completes generation, clean validation, defect injection, CSV detection, scoring and review output. Use a new output directory for each saved run. Failure leaves no final directory, so a folder appearing at the requested path means every workflow stage succeeded. This does not mean real-world data would be error-free: the “success” criterion is agreement with the controlled synthetic fixture.

Read `ISSUES.md` first. It groups multiple checks within one record/category and offers an investigation action. Read `flags.json` for granular check evidence, `evaluation.json` for measured comparisons and `run.json` for the seed/scenario and row counts. Ground truth remains in its own directory. The issue report does not read it.

`workflow.py` uses `TemporaryDirectory` as a context manager. Cleanup happens even if a detector raises an exception. Only after validation does `rename` move the staged result to its final location. An existing directory is refused instead of overwritten. The tests deliberately simulate a failure and protect a pre-existing file to verify both behaviors.

The SQL moved into the Python package's `sql` folder. `pyproject.toml` includes those files as package data and exposes a `claims-quality` command. A wheel is an installable package archive. Testing the wheel from a different working directory catches a common packaging bug: code that works in the repository because its SQL is nearby, but fails after installation because those files were omitted.

`test_ingestion.py` exercises malformed headers, duplicate columns, missing/extra values and useful integer errors. It also preserves schema-valid empty tables. `test_workflow.py` tests repeatability, existing-directory protection, failure cleanup, issue grouping and unknown-category rejection. These checks strengthen execution and interpretation without adding clinical rules.


## 14. Expanded scenarios and enrollment denominators

`scenarios.py` broadens the fixture family beyond header defects. Each named scenario starts from a fresh baseline and records known expected effects before detection. Deleting one provider can flag many referring rows, so a high foreign-key count is not a count of independent source events. A single header can carry three categories while counting only once per category. `expanded.py` saves discrepancies even if they occur; it does not omit failing runs from the report.

`utilization.sql` creates a 12-month calendar and tests enrollment overlap with EXISTS. It counts each member-month once, including months without claims. `cohorts.sql` applies the same denominator and eligibility rules to age groups. A ratio must combine underlying numerators and denominators; adding or unweighted-averaging group PMPM values is wrong. The baseline's 288 member-months are 24 members times 12 covered months. $15,905.27 divided by 288 is about $55.23 per member-month.

`dashboard.py` runs the SQL and exports a self-contained Tableau package plus the underlying monthly/cohort CSVs. Each view filters a separate metric panel so dollars, PMPM values and evaluation counts do not get added together. The executive brief explains what a stakeholder should do differently: verify grain and reconcile before interpreting the numbers. Desktop rendering is a separate acceptance gate from numerical correctness.
