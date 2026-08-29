#!/usr/bin/env python3
"""Move source-named paper directories into the standard catalog layout."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

from stats import CATALOG, ROOT


def unique_destination(directory: Path, filename: str, digest: str) -> Path:
    destination = directory / filename
    if not destination.exists():
        return destination
    return directory / f"{destination.stem}--{digest[:8]}{destination.suffix}"


def layout_moves(rows: list[dict[str, str]]) -> list[tuple[dict[str, str], Path, Path]]:
    """Return safe moves from the legacy source directory to catalog directories."""
    moves: list[tuple[dict[str, str], Path, Path]] = []
    for row in rows:
        relative = Path(row.get("local_path", ""))
        if row.get("availability") != "local" or relative.parts[:2] != ("papers", "deekur"):
            continue
        source = ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(f"catalog file not found: {relative}")
        destination = ROOT / "papers" / row["year"] / row["region"] / row["subject"] / source.name
        destination = unique_destination(destination.parent, destination.name, row["sha256"])
        moves.append((row, source, destination))
    return moves


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="move files and update data/exams.csv")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    moves = layout_moves(rows)
    for _, source, destination in moves:
        print(f"{source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")
    print(f"moves={len(moves)} mode={'apply' if args.apply else 'dry-run'}")
    if not args.apply:
        return 0
    for row, source, destination in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        row["local_path"] = str(destination.relative_to(ROOT))
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
