#!/usr/bin/env python3
"""Classify non-paper materials and place them in dedicated directories."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

from stats import CATALOG, ROOT, classify_material


def unique_destination(directory: Path, filename: str, digest: str) -> Path:
    destination = directory / filename
    if not destination.exists():
        return destination
    return directory / f"{destination.stem}--{digest[:8]}{destination.suffix}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="move files and update the catalog")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    if "material_type" not in fieldnames:
        fieldnames.append("material_type")

    moves: list[tuple[dict[str, str], Path, Path]] = []
    counts: dict[str, int] = {"完整试卷": 0, "附属资料": 0, "片段资料": 0}
    for row in rows:
        category = classify_material(row)
        row["material_type"] = category
        counts[category] += 1
        if category == "完整试卷" or row.get("availability") != "local":
            continue
        source = ROOT / row["local_path"]
        if not source.is_file():
            raise FileNotFoundError(f"catalog file not found: {row['local_path']}")
        collection = "supplements" if category == "附属资料" else "partials"
        destination = ROOT / "papers" / collection / row["year"] / row["region"] / row["subject"] / source.name
        if source != destination:
            destination = unique_destination(destination.parent, destination.name, row.get("sha256", ""))
            moves.append((row, source, destination))

    print(" ".join(f"{name}={count}" for name, count in counts.items()))
    print(f"moves={len(moves)} mode={'apply' if args.apply else 'dry-run'}")
    for row, source, destination in moves:
        print(f"{row['material_type']}: {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")

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
