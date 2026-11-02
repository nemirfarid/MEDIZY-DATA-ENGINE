"""Command-line entry point for safe CSV ingestion."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from .store import insert_records


def main() -> None:
    parser = argparse.ArgumentParser(prog="medizy")
    sub = parser.add_subparsers(dest="command", required=True)
    ingest = sub.add_parser("ingest-csv", help="Import a source CSV into isolated staging")
    ingest.add_argument("--source", required=True, help="Stable source label, e.g. osm")
    ingest.add_argument("--input", required=True, type=Path)
    ingest.add_argument("--db", default=Path("data/staging/medizy_staging.sqlite"), type=Path)
    args = parser.parse_args()

    if args.command == "ingest-csv":
        with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
            records = []
            for row in csv.DictReader(handle):
                row["source"] = args.source
                for key in ("latitude", "longitude"):
                    if row.get(key):
                        row[key] = float(row[key])
                    else:
                        row[key] = None
                records.append(row)
        count = insert_records(args.db, records)
        print(json.dumps({"read": len(records), "inserted": count, "database": str(args.db)}))


if __name__ == "__main__":
    main()
