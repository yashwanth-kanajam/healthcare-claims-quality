"""SQL execution with only five raw tables as inputs. No labels or injection imports."""

from pathlib import Path

import duckdb

from .model import SCHEMA, read_dataset

SQL_DIR = Path(__file__).resolve().parent / "sql"


def connect(data):
    con = duckdb.connect(":memory:")
    try:
        for table, fields in SCHEMA.items():
            columns = ", ".join(
                f'"{name}" {kind} NOT NULL' + (" PRIMARY KEY" if name == "record_id" else "")
                for name, kind in fields.items()
            )
            con.execute(f"CREATE TABLE {table} ({columns})")
            if data[table]:
                con.executemany(
                    f"INSERT INTO {table} VALUES ({', '.join('?' for _ in fields)})",
                    [[row[f] for f in fields] for row in data[table]],
                )
        return con
    except Exception:
        con.close()
        raise


def detect(data):
    con = connect(data)
    try:
        flags = set()
        for name in ("duplicates.sql", "checks.sql"):
            flags.update(con.execute((SQL_DIR / name).read_text()).fetchall())
        return [dict(category=c, table=t, record_id=r, check_name=k) for c, t, r, k in sorted(flags)]
    finally:
        con.close()


def query(data, filename):
    con = connect(data)
    try:
        cursor = con.execute((SQL_DIR / filename).read_text())
        names = [d[0] for d in cursor.description]
        return [dict(zip(names, row, strict=False)) for row in cursor.fetchall()]
    finally:
        con.close()


def detect_directory(directory):
    return detect(read_dataset(directory))
