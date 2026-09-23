"""Post-detection comparison only. Never supplies labels to the detector."""

from .model import CATEGORIES


def key(row):
    return row["category"], row["table"], row["record_id"]


def evaluate(flags, manifest):
    actual = {key(row) for row in flags}
    expected = {key(row) for row in manifest["expected_flags"]}
    metrics = []
    for category in CATEGORIES:
        a = {k for k in actual if k[0] == category}
        e = {k for k in expected if k[0] == category}
        tp, fp, fn = len(a & e), len(a - e), len(e - a)
        metrics.append(
            dict(
                category=category,
                tp=tp,
                fp=fp,
                fn=fn,
                precision=tp / (tp + fp) if tp + fp else None,
                recall=tp / (tp + fn) if tp + fn else None,
            )
        )
    return dict(
        metrics=metrics, false_positives=sorted(actual - expected), false_negatives=sorted(expected - actual)
    )
