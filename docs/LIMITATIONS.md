# Limitations and responsible interpretation

- This is self-generated, controlled synthetic data. It is not anonymized real claims and contains no evidence about actual payer defect prevalence, clinical validity, operational performance or financial savings.
- Held-out seeds change values and locations, not defect mechanisms or table structure. Results measure agreement with auditable fixtures; they do not establish external accuracy, generalization, confidence intervals or production readiness.
- Four categories only. Missingness, key conflicts with differing attributes, code validation, coverage eligibility, overlapping enrollment, units/ranges, unusual utilization, duplicate services, outliers, fraud and compliance assessment are deferred.
- An exact duplicate is based on every business attribute plus identifiers. The rule is intentionally narrower than “same service.” Conversely, structurally consistent records can still be invalid in actual healthcare practice. Different modifiers, units or providers do not prove legitimacy.
- Date and financial contracts are simplified assumptions. Real feeds can include negative reversals, replacements, multiple payment events, coordination of benefits, other-payer amounts, capitation, interest, currency differences, rounding policies and mixed provider roles.
- CSV types and required columns are prerequisites. Bad date strings, null values, missing columns or repeated physical record IDs are ingestion failures, not scored quality events. Errors fail visibly; no silent coercion/imputation is intended.
- Foreign-key existence is not uniqueness. Nonidentical rows sharing a parent ID are unresolved conflicts. Parent-date checks can be ambiguous in such data. Do not run business analytics until keys are validated for the actual source contract.
- No auto-correction, deduplication, clinical coding claim, fraud allegation, adjudication or recovery estimate. Flags are investigation leads.
- Python assertions are used for clean invariants: run normally, not with Python `-O`, which disables assertions. SQL detection still runs independently, but optimized execution is not the documented workflow.
- No real-system adapters or standards compatibility claims (including X12, FHIR or payer extracts). No speed or scale benchmark. DuckDB is local/in-memory, and this fixture is deliberately small.
- Tested environment and dependency versions are documented in VALIDATION.md. Version 0.2 bundles SQL resources in the Python package and validates installed use outside the checkout. Cross-platform validation is still deferred.
- Future work should start with an agreed external data contract and independently labeled samples. Broader domain rules require subject-matter review, separate defect mechanisms and explicit evaluation design, not simply more random seeds.


## Extended analysis boundaries

Utilization eligibility is an analytical filter under the synthetic contract, not a fifth quality category or a real benefit determination. A claim must fit one enrollment span. Adjacent spans are not merged. The dashboard does not establish seasonality, cohort causality or clinical validity. Tableau XML/ZIP validation and reconciled source numbers do not prove rendering; desktop acceptance is tracked separately in dashboard/README.md.
