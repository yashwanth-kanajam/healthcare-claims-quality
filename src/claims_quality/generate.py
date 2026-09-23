"""Deterministic clean fixtures, including structurally valid service lookalikes."""

import random
from datetime import date, timedelta

from .model import KEYS, MONEY, SCHEMA


def generate(seed=17):
    rng = random.Random(seed)
    data = {table: [] for table in SCHEMA}
    for i in range(24):
        data["members"].append(
            dict(record_id=f"M{i:03}", member_id=f"MEM{i:03}", birth_date=f"{1960 + i}-01-01")
        )
        data["enrollment"].append(
            dict(
                record_id=f"E{i:03}",
                enrollment_id=f"ENR{i:03}",
                member_id=f"MEM{i:03}",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )
        )
    for i in range(6):
        data["providers"].append(
            dict(
                record_id=f"P{i:03}",
                provider_id=f"PROV{i:03}",
                provider_type=("SYN_CLINIC", "SYN_LAB")[i % 2],
            )
        )
    for i in range(96):
        member = f"MEM{i % 24:03}"
        provider = f"PROV{i % 6:03}"
        service = date(2024, 1, 1) + timedelta(days=rng.randrange(300))
        h = dict(
            record_id=f"H{i:03}",
            claim_id=f"CLM{i:03}",
            member_id=member,
            provider_id=provider,
            service_start=service.isoformat(),
            service_end=service.isoformat(),
            received_date=(service + timedelta(days=3)).isoformat(),
            paid_date=(service + timedelta(days=10)).isoformat(),
        )
        lines = []
        for j in range(1, 1 + (i % 3 + 1)):
            allowed = rng.randrange(500, 20000)
            patient = allowed // 5
            line = dict(
                record_id=f"L{i:03}_{j}",
                claim_id=h["claim_id"],
                line_number=j,
                provider_id=provider,
                service_start=service.isoformat(),
                service_end=service.isoformat(),
                service_code="SYN_VISIT",
                modifier="SYN_NONE",
                units=1,
                billed_cents=allowed + 1000,
                allowed_cents=allowed,
                paid_cents=allowed - patient,
                patient_cents=patient,
            )
            lines.append(line)
        for field in MONEY:
            h[field] = sum(line[field] for line in lines)
        data["claim_headers"].append(h)
        data["claim_lines"].extend(lines)
    # Two distinct source records with the same apparent service. No adjudication implied.
    import copy

    original = data["claim_headers"][0]
    original_line = data["claim_lines"][0]
    for i, variant in enumerate(("identical_service", "modifier", "units", "provider", "zero_payment"), 96):
        h, line = copy.deepcopy(original), copy.deepcopy(original_line)
        h.update(record_id=f"H{i:03}", claim_id=f"CLM{i:03}")
        line.update(record_id=f"L{i:03}_1", claim_id=h["claim_id"])
        if variant == "modifier":
            line["modifier"] = "SYN_ALT"
        elif variant == "units":
            line["units"] = 2
        elif variant == "provider":
            line["provider_id"] = "PROV001"
            h["provider_id"] = "PROV001"
        elif variant == "zero_payment":
            line["patient_cents"] = line["allowed_cents"]
            line["paid_cents"] = 0
        for field in MONEY:
            h[field] = line[field]
        data["claim_headers"].append(h)
        data["claim_lines"].append(line)
    return data


def validate_clean(data):
    """Independent Python assertions; never calls the SQL detector or manifest."""
    for table, rows in data.items():
        assert len({r["record_id"] for r in rows}) == len(rows)
        assert len({tuple(r[k] for k in KEYS[table]) for r in rows}) == len(rows)
    members = {r["member_id"]: r for r in data["members"]}
    providers = {r["provider_id"] for r in data["providers"]}
    headers = {r["claim_id"]: r for r in data["claim_headers"]}
    for e in data["enrollment"]:
        assert e["member_id"] in members
        assert date.fromisoformat(e["start_date"]) <= date.fromisoformat(e["end_date"])
    for h in headers.values():
        assert h["member_id"] in members and h["provider_id"] in providers
        assert (
            members[h["member_id"]]["birth_date"]
            <= h["service_start"]
            <= h["service_end"]
            <= h["received_date"]
            <= h["paid_date"]
        )
        assert any(
            e["member_id"] == h["member_id"]
            and e["start_date"] <= h["service_start"] <= h["service_end"] <= e["end_date"]
            for e in data["enrollment"]
        )
        lines = [r for r in data["claim_lines"] if r["claim_id"] == h["claim_id"]]
        assert lines
        for field in MONEY:
            assert h[field] == sum(r[field] for r in lines)
    for line in data["claim_lines"]:
        assert line["claim_id"] in headers and line["provider_id"] in providers
        h = headers[line["claim_id"]]
        assert h["service_start"] <= line["service_start"] <= line["service_end"] <= h["service_end"]
        assert line["units"] > 0
    for r in data["claim_headers"] + data["claim_lines"]:
        assert all(r[f] >= 0 for f in MONEY)
        assert r["billed_cents"] >= r["allowed_cents"] == r["paid_cents"] + r["patient_cents"]
