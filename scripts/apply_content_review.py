#!/usr/bin/env python3
"""Apply evidence-backed duplicate review decisions to the paper catalog."""

from __future__ import annotations

import argparse
import csv
import shutil
from pathlib import Path

from normalize_paper_layout import unique_destination
from stats import CATALOG, ROOT

# Decisions are based on the reviewed content, not filename or byte hash alone.
REMOVE_IDS = {
    "temp-2023-物理-0a21a26edf23",  # Knowledge-point material, not the nationwide paper.
    "temp-2025-物理-1021d1a86165",  # Same answered 安徽卷 as the retained GitHub version.
    "deekur-2025-53-math",  # Two-column reflow of the retained 5-page 北京卷 scan.
    "temp-2025-物理-69203d072e93",  # Same answered 广东卷 as the retained GitHub version.
    "temp-2025-物理-4f75fa4ef7ba",  # Same answered 湖南卷 as the retained GitHub version.
    "temp-2025-物理-7b831f1303b3",  # Same answered 江苏卷 as the retained GitHub version.
    "temp-2025-物理-19f9ce751abe",  # Same 上海卷 with answers; GitHub version retained instead.
    "temp-2025-物理-ac4daff519b4",  # Same 云南卷 with answers; GitHub version retained instead.
}
SUPPLEMENT_IDS = {
    "temp-2022-语文-9fee8807a6cc",  # Same 全国乙卷 with an added model essay.
    "deekur-2025-physics-029",  # 安徽卷 with answers.
    "deekur-2025-physics-031",  # 广东卷 with detailed answers.
    "deekur-2025-physics-036",  # 河南卷 with detailed answers.
    "deekur-2025-physics-041",  # 湖南卷 with detailed answers.
    "deekur-2025-physics-033",  # 江苏卷 with detailed answers.
    "deekur-2025-physics-023",  # 上海卷 with detailed answers.
    "deekur-2025-physics-024",  # 云南卷 with detailed answers.
}
PARTIAL_IDS = {
    "temp-2025-物理-d1cb17271a18",  # One-page 四川卷回忆版，仅含第 14、15 题。
}
CONFLICTS = {
    "deekur-2026-58-math": "内容复核：与 temp-2026-数学-b4cda6722b5f 存在实质题干差异，暂不合并，待官方来源核验。",
    "temp-2026-数学-b4cda6722b5f": "内容复核：与 deekur-2026-58-math 存在实质题干差异，暂不合并，待官方来源核验。",
    "deekur-2026-55-math": "内容复核：与 temp-2026-数学-66df94475d50 存在实质题干差异，暂不合并，待官方来源核验。",
    "temp-2026-数学-66df94475d50": "内容复核：与 deekur-2026-55-math 存在实质题干差异，暂不合并，待官方来源核验。",
    "deekur-2026-59-math": "内容复核：与 temp-2026-数学-9c9cb50bcd0c 存在实质题干差异，暂不合并，待官方来源核验。",
    "temp-2026-数学-9c9cb50bcd0c": "内容复核：与 deekur-2026-59-math 存在实质题干差异，暂不合并，待官方来源核验。",
}


def review_action(record_id: str) -> str:
    if record_id in REMOVE_IDS:
        return "remove"
    if record_id in SUPPLEMENT_IDS:
        return "supplement"
    if record_id in PARTIAL_IDS:
        return "partial"
    return "keep"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="apply reviewed moves, removals, and metadata notes")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)

    known_ids = {row["record_id"] for row in rows}
    expected_ids = REMOVE_IDS | SUPPLEMENT_IDS | PARTIAL_IDS | set(CONFLICTS)
    missing = expected_ids - known_ids
    if missing:
        raise ValueError(f"review record ids not found: {', '.join(sorted(missing))}")

    moves: list[tuple[dict[str, str], Path, Path, str]] = []
    removals: list[tuple[dict[str, str], Path]] = []
    for row in rows:
        action = review_action(row["record_id"])
        if action == "keep":
            continue
        source = ROOT / row["local_path"]
        if not source.is_file():
            raise FileNotFoundError(f"catalog file not found: {row['local_path']}")
        if action == "remove":
            removals.append((row, source))
            continue
        collection = "supplements" if action == "supplement" else "partials"
        destination = ROOT / "papers" / collection / row["year"] / row["region"] / row["subject"] / source.name
        destination = unique_destination(destination.parent, destination.name, row["sha256"])
        moves.append((row, source, destination, action))

    for row, source in removals:
        print(f"remove {row['record_id']}: {source.relative_to(ROOT)}")
    for row, source, destination, action in moves:
        print(f"{action} {row['record_id']}: {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")
    print(f"removals={len(removals)} moves={len(moves)} conflicts={len(CONFLICTS)} mode={'apply' if args.apply else 'dry-run'}")
    if not args.apply:
        return 0

    remove_ids = {row["record_id"] for row, _ in removals}
    for _, source in removals:
        source.unlink()
    for row, source, destination, action in moves:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(source, destination)
        row["local_path"] = str(destination.relative_to(ROOT))
        row["material_type"] = "附属资料" if action == "supplement" else "片段资料"
        row["paper_type"] = "试题答案解析" if action == "supplement" else "部分试题"
        row["notes"] = f"{row['notes']}；内容复核后归类为{row['material_type']}"
    for row in rows:
        if row["record_id"] in CONFLICTS and CONFLICTS[row["record_id"]] not in row["notes"]:
            row["notes"] = f"{row['notes']}；{CONFLICTS[row['record_id']]}"
    rows = [row for row in rows if row["record_id"] not in remove_ids]
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
