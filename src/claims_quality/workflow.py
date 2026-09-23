"""Reproducible, isolated synthetic runs and a label-free issue review report."""

import json
import tempfile
from collections import Counter
from pathlib import Path

from .detect import detect_directory, query
from .evaluate import evaluate
from .generate import generate, validate_clean
from .inject import inject
from .model import CATEGORIES, write_dataset

GUIDANCE = {
    "exact_duplicate": "Compare source provenance for every occurrence before deciding which record to retain. Similar services with different identifiers are not judged here.",
    "broken_foreign_key": "Locate the referenced parent in the source extract; investigate missing files, identifiers or load order before repairing a relationship.",
    "invalid_date_sequence": "Confirm date-field definitions and compare source dates. These checks implement the synthetic contract, not universal payer rules.",
    "financial_reconciliation": "Compare all four amounts at header and line grain; investigate allocation errors, missing/repeated lines and cascades. Do not sum flagged dollars as recoverable money.",
}


def escape(value):
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ")


def review_text(flags):
    """Does not accept or read a manifest; reports observations, not known truth."""
    grouped = {}
    for row in flags:
        category = row["category"]
        if category not in CATEGORIES:
            raise ValueError("Unknown flag category: " + category)
        grouped.setdefault((category, row["table"], row["record_id"]), set()).add(row["check_name"])
    counts = Counter(k[0] for k in grouped)
    unique_checks = sum(len(v) for v in grouped.values())
    lines = [
        "# Issue review",
        "",
        f"{unique_checks} distinct check-level flags; **{len(grouped)} record/category issues**. Multiple checks on one record in a category are grouped together.",
        "",
        "This report uses detector output only. Flags require investigation; they are not confirmed fraud, invalid clinical services, or automatically approved corrections. One source event can affect both a line and its header.",
        "",
        "| Category | Record/category issues |",
        "|---|---:|",
    ]
    for category in CATEGORIES:
        lines.append(f"| {category} | {counts[category]} |")
    if not grouped:
        lines += [
            "",
            "No flags were produced by these four checks. This does not certify the data beyond the declared contract.",
        ]
    for category in CATEGORIES:
        items = [(t, r, checks) for (c, t, r), checks in sorted(grouped.items()) if c == category]
        if not items:
            continue
        lines += [
            "",
            "## " + category,
            "",
            GUIDANCE[category],
            "",
            "| Table | Physical record ID | Checks |",
            "|---|---|---|",
        ]
        for table, record, checks in items:
            lines.append(f"| {escape(table)} | {escape(record)} | {escape(', '.join(sorted(checks)))} |")
    return "\n".join(lines) + "\n"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def run(out, seed=17, scenario="standard"):
    """Publish a new directory only after every stage succeeds; never overwrite a run."""
    out = Path(out).resolve()
    if out.exists():
        raise ValueError("Output already exists; choose a new run directory: " + str(out))
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".claims-run-", dir=out.parent) as temporary:
        stage = Path(temporary) / "result"
        stage.mkdir()
        clean = generate(seed)
        validate_clean(clean)
        write_dataset(clean, stage / "clean")
        clean_flags = detect_directory(stage / "clean")
        if clean_flags:
            raise ValueError("Clean baseline failed SQL checks")
        dirty, manifest = inject(clean, seed, scenario)
        write_dataset(dirty, stage / "dirty")
        flags = detect_directory(stage / "dirty")
        evaluation = evaluate(flags, manifest)
        if evaluation["false_positives"] or evaluation["false_negatives"]:
            raise ValueError("Evaluation differs from the controlled manifest; run not published")
        (stage / "ground_truth").mkdir()
        write_json(stage / "ground_truth" / "manifest.json", manifest)
        write_json(stage / "flags.json", flags)
        write_json(stage / "evaluation.json", evaluation)
        write_json(stage / "analytics.json", query(clean, "analytics.sql")[0])
        (stage / "ISSUES.md").write_text(review_text(flags))
        write_json(
            stage / "run.json",
            dict(
                seed=seed,
                scenario=scenario,
                dataset="self-generated synthetic",
                clean_row_counts={t: len(v) for t, v in clean.items()},
                dirty_row_counts={t: len(v) for t, v in dirty.items()},
                check_flags=len(flags),
                evaluation_units=len({(f["category"], f["table"], f["record_id"]) for f in flags}),
                ground_truth_used_by_detector=False,
            ),
        )
        stage.rename(out)
    return out
