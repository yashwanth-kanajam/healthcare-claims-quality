"""Explicit raw-table contracts. Money is integer cents, dates are ISO dates."""

import csv
from pathlib import Path

SCHEMA = {
    "members": {"record_id": "VARCHAR", "member_id": "VARCHAR", "birth_date": "DATE"},
    "providers": {"record_id": "VARCHAR", "provider_id": "VARCHAR", "provider_type": "VARCHAR"},
    "enrollment": {
        "record_id": "VARCHAR",
        "enrollment_id": "VARCHAR",
        "member_id": "VARCHAR",
        "start_date": "DATE",
        "end_date": "DATE",
    },
    "claim_headers": {
        "record_id": "VARCHAR",
        "claim_id": "VARCHAR",
        "member_id": "VARCHAR",
        "provider_id": "VARCHAR",
        "service_start": "DATE",
        "service_end": "DATE",
        "received_date": "DATE",
        "paid_date": "DATE",
        "billed_cents": "BIGINT",
        "allowed_cents": "BIGINT",
        "paid_cents": "BIGINT",
        "patient_cents": "BIGINT",
    },
    "claim_lines": {
        "record_id": "VARCHAR",
        "claim_id": "VARCHAR",
        "line_number": "INTEGER",
        "provider_id": "VARCHAR",
        "service_start": "DATE",
        "service_end": "DATE",
        "service_code": "VARCHAR",
        "modifier": "VARCHAR",
        "units": "INTEGER",
        "billed_cents": "BIGINT",
        "allowed_cents": "BIGINT",
        "paid_cents": "BIGINT",
        "patient_cents": "BIGINT",
    },
}
KEYS = {
    "members": ("member_id",),
    "providers": ("provider_id",),
    "enrollment": ("enrollment_id",),
    "claim_headers": ("claim_id",),
    "claim_lines": ("claim_id", "line_number"),
}
MONEY = ("billed_cents", "allowed_cents", "paid_cents", "patient_cents")
CATEGORIES = ("exact_duplicate", "broken_foreign_key", "invalid_date_sequence", "financial_reconciliation")


def write_dataset(data, directory):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for table, fields in SCHEMA.items():
        with (directory / (table + ".csv")).open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(data[table])


def read_dataset(directory):
    result = {}
    for table, fields in SCHEMA.items():
        with (Path(directory) / (table + ".csv")).open(newline="") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames
            if columns is None or len(columns) != len(fields) or set(columns) != set(fields):
                raise ValueError("Unexpected columns in " + table)
            rows = []
            for row in reader:
                if set(row) != set(fields) or any(value is None or value == "" for value in row.values()):
                    raise ValueError(f"Missing or extra values in {table} at CSV line {reader.line_num}")
                for field, kind in fields.items():
                    if kind in ("INTEGER", "BIGINT"):
                        try:
                            row[field] = int(row[field])
                        except ValueError as error:
                            raise ValueError(
                                f"Invalid integer in {table}.{field} at CSV line {reader.line_num}"
                            ) from error
                rows.append(row)
        result[table] = rows
    return result
