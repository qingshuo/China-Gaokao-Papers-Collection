#!/usr/bin/env python3
"""Remove exact catalog duplicates when a PDF and editable format share one title."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from stats import CATALOG, ROOT


def pdf_format_duplicates(rows: list[dict[str, str]], year: str) -> list[tuple[dict[str, str], dict[str, str]]]:
    """Return (keep_pdf, remove_editable) pairs with identical catalog identity."""
    groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
    fields = ("year", "region", "subject", "paper_type", "material_type", "title")
    for row in rows:
        if row.get("year") == year and row.get("availability") == "local":
            groups[tuple(row.get(field, "") for field in fields)].append(row)

    duplicates: list[tuple[dict[str, str], dict[str, str]]] = []
    for group in groups.values():
        extensions = {Path(row["local_path"]).suffix.lower() for row in group}
        if len(group) != 2 or ".pdf" not in extensions or not extensions & {".doc", ".docx"}:
            continue
        keep = next(row for row in group if Path(row["local_path"]).suffix.lower() == ".pdf")
        remove = next(row for row in group if row is not keep)
        duplicates.append((keep, remove))
    return duplicates


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, help="year to examine")
    parser.add_argument("--apply", action="store_true", help="delete editable duplicates and update the catalog")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    duplicates = pdf_format_duplicates(rows, args.year)
    total_bytes = 0
    for keep, remove in duplicates:
        path = ROOT / remove["local_path"]
        if not path.is_file():
            raise FileNotFoundError(f"catalog file not found: {remove['local_path']}")
        total_bytes += path.stat().st_size
        print(f"keep {keep['local_path']}\nremove {remove['local_path']}")
    print(f"pairs={len(duplicates)} bytes_to_remove={total_bytes} mode={'apply' if args.apply else 'dry-run'}")

    if not args.apply:
        return 0
    remove_paths = {row["local_path"] for _, row in duplicates}
    for relative_path in remove_paths:
        (ROOT / relative_path).unlink()
    kept_rows = [row for row in rows if row.get("local_path") not in remove_paths]
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(kept_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
