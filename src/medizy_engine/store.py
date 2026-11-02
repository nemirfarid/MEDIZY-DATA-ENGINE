"""Isolated staging database. This module never opens or modifies the MEDIZY production DB."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS staged_facilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT NOT NULL,
    source_id TEXT,
    name TEXT,
    category TEXT,
    wilaya TEXT,
    address TEXT,
    phone TEXT,
    latitude REAL,
    longitude REAL,
    raw_json TEXT NOT NULL,
    imported_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_staged_name ON staged_facilities(name);
CREATE INDEX IF NOT EXISTS idx_staged_wilaya ON staged_facilities(wilaya);
CREATE INDEX IF NOT EXISTS idx_staged_phone ON staged_facilities(phone);
"""


def initialize(path: str | Path) -> None:
    db_path = Path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript(SCHEMA)


def insert_records(path: str | Path, records: list[dict[str, Any]]) -> int:
    """Insert source records into staging; existing source IDs are not overwritten."""
    initialize(path)
    inserted = 0
    with sqlite3.connect(path) as conn:
        for record in records:
            source = str(record.get("source") or "").strip()
            if not source:
                raise ValueError("Every record must include a non-empty 'source'.")
            source_id = record.get("source_id")
            cursor = conn.execute(
                """INSERT OR IGNORE INTO staged_facilities
                (source, source_id, name, category, wilaya, address, phone,
                 latitude, longitude, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    source, source_id, record.get("name"), record.get("category"),
                    record.get("wilaya"), record.get("address"), record.get("phone"),
                    record.get("latitude"), record.get("longitude"),
                    json.dumps(record, ensure_ascii=False, sort_keys=True),
                ),
            )
            inserted += cursor.rowcount
    return inserted
