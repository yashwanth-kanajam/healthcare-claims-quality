"""Broader auditable fixtures: explicit expected labels, never detector-derived."""

import copy
import random
from datetime import date, timedelta

SCENARIOS = (
    "duplicate_member",
    "duplicate_provider",
    "duplicate_enrollment",
    "duplicate_line",
    "orphan_enrollment",
    "orphan_member",
    "orphan_line",
    "orphan_line_provider",
    "enrollment_reversed",
    "line_reversed",
    "member_born_after_service",
    "missing_claim_lines",
    "negative_header_payment",
    "line_billed_below_allowed",
    "overlapping_header_failures",
    "missing_provider_cascade",
    "valid_equal_dates",
    "valid_multiday_claim",
)


def build_scenario(clean, name, seed=17):
    if name not in SCENARIOS:
        raise ValueError("Unknown expanded scenario: " + name)
    data = copy.deepcopy(clean)
    rng = random.Random(seed + 20000)
    h = rng.choice(data["claim_headers"][:96])
    line = next(ln for ln in data["claim_lines"] if ln["claim_id"] == h["claim_id"])
    labels = {}
    events = []

    def mark(category, table, row, reason):
        labels.setdefault((category, table, row["record_id"]), []).append(reason)

    def change(table, row, reason):
        events.append(dict(table=table, record_id=row["record_id"], description=reason))

    if name.startswith("duplicate_"):
        table = {
            "duplicate_member": "members",
            "duplicate_provider": "providers",
            "duplicate_enrollment": "enrollment",
            "duplicate_line": "claim_lines",
        }[name]
        row = line if table == "claim_lines" else rng.choice(data[table])
        duplicate = dict(row, record_id=row["record_id"] + "_REPEAT")
        data[table].append(duplicate)
        for item in (row, duplicate):
            mark(
                "exact_duplicate", table, item, "Identical business fields; both source occurrences expected"
            )
        if table == "claim_lines":
            mark("financial_reconciliation", "claim_headers", h, "Repeated line increases all line totals")
        change(table, duplicate, "Repeat one complete business record")
    elif name == "orphan_enrollment":
        row = rng.choice(data["enrollment"])
        row["member_id"] = "MISSING"
        mark("broken_foreign_key", "enrollment", row, "Enrollment member missing")
        change("enrollment", row, "Replace member reference")
    elif name == "orphan_member":
        h["member_id"] = "MISSING"
        mark("broken_foreign_key", "claim_headers", h, "Header member missing")
        change("claim_headers", h, "Replace member reference")
    elif name in ("orphan_line", "orphan_line_provider"):
        field = "claim_id" if name == "orphan_line" else "provider_id"
        line[field] = "MISSING"
        mark("broken_foreign_key", "claim_lines", line, "Line parent reference missing")
        if name == "orphan_line":
            mark("financial_reconciliation", "claim_headers", h, "Original claim loses the moved line amount")
        change("claim_lines", line, "Replace " + field)
    elif name == "enrollment_reversed":
        row = rng.choice(data["enrollment"])
        row["end_date"] = "2023-12-31"
        mark("invalid_date_sequence", "enrollment", row, "Coverage end before start")
        change("enrollment", row, "Reverse coverage period")
    elif name == "line_reversed":
        line["service_start"] = (date.fromisoformat(line["service_end"]) + timedelta(days=1)).isoformat()
        mark("invalid_date_sequence", "claim_lines", line, "Line starts after its end and outside header")
        change("claim_lines", line, "Reverse line period")
    elif name == "member_born_after_service":
        row = next(m for m in data["members"] if m["member_id"] == h["member_id"])
        row["birth_date"] = "2025-01-01"
        for header in data["claim_headers"]:
            if header["member_id"] == row["member_id"]:
                mark(
                    "invalid_date_sequence",
                    "claim_headers",
                    header,
                    "Known cascade: referenced birth after all 2024 services",
                )
        change("members", row, "Change birth date; affected unit is each referencing header")
    elif name == "missing_claim_lines":
        data["claim_lines"] = [ln for ln in data["claim_lines"] if ln["claim_id"] != h["claim_id"]]
        mark("financial_reconciliation", "claim_headers", h, "No supporting lines")
        change("claim_headers", h, "Remove all child lines; header retained")
    elif name == "negative_header_payment":
        h["paid_cents"] = -1
        h["patient_cents"] = h["allowed_cents"] + 1
        mark(
            "financial_reconciliation",
            "claim_headers",
            h,
            "Allocation balances but negative payment violates contract",
        )
        change("claim_headers", h, "Set negative paid; preserve allocation equality")
    elif name == "line_billed_below_allowed":
        line["billed_cents"] = line["allowed_cents"] - 1
        mark("financial_reconciliation", "claim_lines", line, "Billed below allowed")
        mark("financial_reconciliation", "claim_headers", h, "Changed billed line total no longer reconciles")
        change("claim_lines", line, "Reduce billed amount below allowed")
    elif name == "overlapping_header_failures":
        h["provider_id"] = "MISSING"
        h["paid_date"] = h["service_start"]
        h["paid_cents"] += 1
        for category, reason in (
            ("broken_foreign_key", "Missing provider"),
            ("invalid_date_sequence", "Paid before receipt"),
            ("financial_reconciliation", "Paid amount changed"),
        ):
            mark(category, "claim_headers", h, reason)
        change("claim_headers", h, "Three categories on one row")
    elif name == "missing_provider_cascade":
        provider = h["provider_id"]
        row = next(p for p in data["providers"] if p["provider_id"] == provider)
        data["providers"] = [p for p in data["providers"] if p["provider_id"] != provider]
        for table in ("claim_headers", "claim_lines"):
            for child in data[table]:
                if child["provider_id"] == provider:
                    mark(
                        "broken_foreign_key",
                        table,
                        child,
                        "Known cascade from deleted provider dimension record",
                    )
        change("providers", row, "Remove dimension row; label every referencing child")
    elif name == "valid_equal_dates":
        h["received_date"] = h["paid_date"] = h["service_end"]
        change("claim_headers", h, "Valid boundary: receipt/payment equal service end")
    elif name == "valid_multiday_claim":
        end = date.fromisoformat(h["service_start"]) + timedelta(days=2)
        h["service_end"] = end.isoformat()
        h["received_date"] = (end + timedelta(days=3)).isoformat()
        h["paid_date"] = (end + timedelta(days=10)).isoformat()
        line["service_end"] = h["service_end"]
        change("claim_headers", h, "Valid multi-day window with contained lines")
    expected = [
        dict(category=c, table=t, record_id=r, reasons=why) for (c, t, r), why in sorted(labels.items())
    ]
    return data, dict(
        seed=seed,
        scenario=name,
        evaluation_unit="category/table/physical record_id",
        expected_flags=expected,
        injection_events=events,
    )
