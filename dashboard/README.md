# Tableau dashboard

Open `Claims_Quality_Public.twbx` locally in Tableau Public 2026.2.2. The package contains the Hyper extract and source CSV. Alternatively, open `Claims_Quality_Public.twb` with the adjacent `Data/` directory intact. No account, server or public upload is needed. Do not use Save to Tableau Public.

All data are fabricated. These results do not describe real patients or payer performance.

Four panels use separate filters and units:

1. Incorrect header-line join ($37,011.02) versus correct header and line totals ($15,905.27 each). The join repeats each header payment once per line, overstating paid spending by $21,105.75.
2. Monthly paid amounts, totaling $15,905.27. November and December correctly show zero: service dates are generated in the first 300 days of 2024, while enrollment continues through December.
3. Paid per enrolled member-month: 54.897333333333336 USD for age 55 and over, and 55.461845238095236 USD for under 55. Rates must not be summed.
4. Expanded evaluation true-positive units: 32 exact duplicates, 236 broken references, 28 invalid date sequences, and 28 financial reconciliation findings. Units are scenario-run/category/physical-row combinations, not independent real-world events.

Axis titles identify their units and category labels are human-readable. Display rounding does not change source values.

## Reproduce from the repository root

```sh
python3 -m venv .venv
.venv/bin/python -m pip install '.[tableau]'
.venv/bin/claims-quality dashboard --out work/tableau-build
.venv/bin/claims-quality tableau-extract --data work/tableau-build
```

Open `work/tableau-build/Claims_Quality_Public.twbx`. The CSV-only `Claims_Quality.twbx` is retained for Tableau Desktop; Tableau Public requires the extract-backed package.

The official Hyper API dependency is pinned and usage telemetry is disabled. The converter reads every extracted value back and compares it with the CSV before packaging. Hyper binaries may contain internal metadata and are not claimed to be byte-identical across builds. Installation was checked on macOS arm64 with Python 3.11.5; other platforms remain unverified.

## Workbook verification

The extract-backed workbook opens and all four panels render in Tableau Public 2026.2.2. Financial, monthly, cohort and evaluation values reconcile to the source results. See the [validation summary](../reports/VALIDATION_SUMMARY.md).

Generated validation JSON retains `tableau_rendering_verified=false`, because generating the workbook cannot by itself certify how Tableau will render it. Rendering was confirmed by opening the workbook.

References: [packaged workbooks](https://help.tableau.com/current/pro/desktop/en-us/save_savework_packagedworkbooks.htm) and [Hyper extracts](https://tableau.github.io/hyper-db/docs/guides/hyper_file/create_update/).

No Tableau sample data or dashboard assets are included. Installed sample workbooks were used only to check XML structural conventions.
