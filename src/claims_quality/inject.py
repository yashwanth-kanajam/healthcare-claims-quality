"""Fixture construction and truth labeling only. Detector never imports this module."""

import copy
import random


def inject(clean, seed=17, scenario="standard"):
    if scenario not in ("sparse", "standard", "stress"):
        raise ValueError("Unknown scenario: " + scenario)
    data = copy.deepcopy(clean)
    truth = {}
    events = []

    def mark(category, table, record, reason):
        key = (category, table, record["record_id"])
        truth.setdefault(key, []).append(reason)

    def event(kind, table, row, description):
        events.append(dict(kind=kind, table=table, record_id=row["record_id"], description=description))

    rng = random.Random(seed + 10000)
    # Separate claims isolate causes; reserve valid edge cases H096..H100.
    claims = rng.sample(data["claim_headers"][:96], 12)
    factor = {"sparse": 1, "standard": 2, "stress": 3}[scenario]
    for i in range(factor):
        h = claims[i]
        duplicate = copy.deepcopy(h)
        duplicate["record_id"] = h["record_id"] + "_COPY"
        data["claim_headers"].append(duplicate)
        for row in (h, duplicate):
            mark("exact_duplicate", "claim_headers", row, "All business fields repeated, including claim_id")
        event(
            "duplicate_header",
            "claim_headers",
            duplicate,
            "Copy header, retain business identifier; label both occurrences",
        )
        h = claims[3 + i]
        h["provider_id"] = "MISSING_PROVIDER"
        mark("broken_foreign_key", "claim_headers", h, "Provider missing from provider table")
        event("missing_provider", "claim_headers", h, "Replace header provider with nonexistent ID")
        h = claims[6 + i]
        h["paid_date"] = h["service_start"]
        mark(
            "invalid_date_sequence",
            "claim_headers",
            h,
            "Payment precedes receipt under this fixture's date contract",
        )
        event("payment_before_receipt", "claim_headers", h, "Set payment earlier than receipt")
        h = claims[9 + i]
        h["paid_cents"] += 137
        mark(
            "financial_reconciliation",
            "claim_headers",
            h,
            "Header allocation and header-to-line payment mismatch",
        )
        event("header_payment_error", "claim_headers", h, "Add 137 cents to header paid only")
    if scenario == "stress":
        # A line-level error intentionally propagates to its header reconciliation.
        reserved = {h["claim_id"] for h in claims}
        h = next(h for h in data["claim_headers"][:96] if h["claim_id"] not in reserved)
        line = next(r for r in data["claim_lines"] if r["claim_id"] == h["claim_id"])
        line["paid_cents"] += 29
        mark("financial_reconciliation", "claim_lines", line, "Line allocation mismatch")
        mark(
            "financial_reconciliation",
            "claim_headers",
            h,
            "Expected cascade: header no longer reconciles to changed line",
        )
        event("line_payment_error", "claim_lines", line, "Add 29 cents; label line plus affected header")
    manifest = [
        dict(category=c, table=t, record_id=r, reasons=why) for (c, t, r), why in sorted(truth.items())
    ]
    return data, {
        "seed": seed,
        "scenario": scenario,
        "evaluation_unit": "category/table/physical record_id",
        "expected_flags": manifest,
        "injection_events": events,
    }
