"""Measured scenario matrix including explicit cascades and valid edge cases."""

import json
from pathlib import Path

from .detect import detect
from .evaluate import evaluate
from .generate import generate, validate_clean
from .model import CATEGORIES
from .scenarios import SCENARIOS, build_scenario

SEEDS = (17, 101, 202, 303)


def build_expanded_report(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    runs = []
    for seed in SEEDS:
        clean = generate(seed)
        validate_clean(clean)
        for name in SCENARIOS:
            data, manifest = build_scenario(clean, name, seed)
            if name.startswith("valid_"):
                validate_clean(data)
            flags = detect(data)
            runs.append(
                dict(
                    seed=seed,
                    scenario=name,
                    events=len(manifest["injection_events"]),
                    expected_units=len(manifest["expected_flags"]),
                    **evaluate(flags, manifest),
                )
            )
    metrics = []
    for c in CATEGORIES:
        rows = [m for r in runs for m in r["metrics"] if m["category"] == c]
        tp, fp, fn = (sum(m[k] for m in rows) for k in ("tp", "fp", "fn"))
        metrics.append(
            dict(
                category=c,
                tp=tp,
                fp=fp,
                fn=fn,
                precision=tp / (tp + fp) if tp + fp else None,
                recall=tp / (tp + fn) if tp + fn else None,
            )
        )
    payload = dict(seeds=SEEDS, scenarios=SCENARIOS, aggregate_metrics=metrics, runs=runs)
    (out / "expanded-results.json").write_text(json.dumps(payload, indent=2) + "\n")
    failures = [r for r in runs if r["false_positives"] or r["false_negatives"]]
    lines = [
        "# Expanded controlled evaluation",
        "",
        f"{len(runs)} scenario/seed runs across {len(SCENARIOS)} named mechanisms and edge cases. {len(failures)} runs disagree with expected labels.",
        "",
        "Labels describe known mutations and their downstream effects; SQL never receives the labels. Evaluation unit is scenario-run/category/table/physical record ID. Multiple checks in one category collapse; deleted parent rows are not themselves flagged when absent. Their referring records are evaluated.",
        "",
        "| Category | TP | FP | FN | Precision | Recall |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for m in metrics:
        lines.append(
            f"| {m['category']} | {m['tp']} | {m['fp']} | {m['fn']} | {m['precision']} | {m['recall']} |"
        )
    lines += [
        "",
        "| Scenario | Runs | Expected units across seeds | False positives | Missed units |",
        "|---|---:|---:|---:|---:|",
    ]
    for name in SCENARIOS:
        rows = [r for r in runs if r["scenario"] == name]
        lines.append(
            f"| {name} | {len(rows)} | {sum(r['expected_units'] for r in rows)} | {sum(len(r['false_positives']) for r in rows)} | {sum(len(r['false_negatives']) for r in rows)} |"
        )
    lines += [
        "",
        "Full discrepant tuples and per-category denominators are preserved in expanded-results.json. Undefined precision/recall is null, including valid-only scenarios. Perfect controlled scores are not external healthcare accuracy. These scenarios broaden tested mechanisms within the same four categories; they do not validate clinical legitimacy or real payer formats.",
        "",
        "The missing-provider and birth-date cases label known referencing children explicitly. The overlap case counts one header in three categories. The duplicate-line, orphan-line and line-billed cases count expected header reconciliation consequences. Cases are evaluated independently rather than mixed into one ambiguous master dataset.",
        "",
    ]
    (out / "EXPANDED_RESULTS.md").write_text("\n".join(lines))
    return payload
