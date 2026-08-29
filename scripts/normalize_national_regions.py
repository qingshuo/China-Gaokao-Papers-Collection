#!/usr/bin/env python3
"""Place explicitly nationwide paper records under the nationwide region."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

from normalize_paper_layout import unique_destination
from stats import CATALOG, ROOT


def is_nationwide_paper(row: dict[str, str]) -> bool:
    """Match records whose titles explicitly identify a nationwide paper."""
    return row.get("region") != "全国" and "全国" in row.get("title", "")


def national_region_moves(rows: list[dict[str, str]]) -> list[tuple[dict[str, str], Path, Path]]:
    moves: list[tuple[dict[str, str], Path, Path]] = []
    for row in rows:
        if not is_nationwide_paper(row) or row.get("availability") != "local":
            continue
        source = ROOT / row["local_path"]
        if not source.is_file():
            raise FileNotFoundError(f"catalog file not found: {row['local_path']}")
        destination = ROOT / "papers" / row["year"] / "全国" / row["subject"] / source.name
        destination = unique_destination(destination.parent, destination.name, row["sha256"])
        moves.append((row, source, destination))
    return moves


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="move files and update region fields")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    moves = national_region_moves(rows)
    for row, source, destination in moves:
        print(f"{row['region']} -> 全国: {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")
    print(f"moves={len(moves)} mode={'apply' if args.apply else 'dry-run'}")
    if not args.apply:
        return 0
    for row, source, destination in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        row["region"] = "全国"
        row["local_path"] = str(destination.relative_to(ROOT))
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
