#!/usr/bin/env python3
"""Apply explicitly reviewed replacements from the temp-v2 collection.

Every entry names both expected file hashes.  A matching filename, catalogue
identity, or page count is deliberately insufficient to overwrite a paper.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import tempfile
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, ROOT

REPLACEMENTS = {
    "temp-2024-政治-8360f67645d2": {
        "source": "temp/版本2：政治（按省份分类）2008-2024/2008-2024·（山东）政治高考真题/2024年高考政治试卷（山东）（空白卷）.pdf",
        "old_sha256": "8360f67645d2b3c13eb4ae2acec799a9bf1ab43db678fbe3f33bc8efbeeb1c4b",
        "new_sha256": "670459b88c6624489c0cb13ff1cf4e7631ac38fcd3b2a5496cef1d4741e3c4e1",
        "title": "2024年全省普通高中学业水平等级考试思想政治",
        "paper_type": "山东卷",
        "note": (
            "内容复核：全文题干相似度 0.953；逐页视觉抽样确认选择题、图表材料及第 18–19 题一致。"
            "新版本保留“共 8 页”页码及完整正式页眉，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-政治-1e6d66279d3e": {
        "source": "temp/版本2：政治（按省份分类）2008-2024/2008-2024·（湖南）政治高考真题/2024年高考政治试卷（湖南）（空白卷）.pdf",
        "old_sha256": "1e6d66279d3ebb5075df46b4b565c5ec0d49d5f468d5ddd01b92a5b8991c447e",
        "new_sha256": "3b5e2b1bbdab2f3c82b4948db068fc94e93458f0775d5bb993a96c0b8f2fda4f",
        "title": "2024年湖南省普通高中学业水平选择性考试思想政治",
        "paper_type": "湖南卷",
        "note": (
            "内容复核：全文题干相似度 0.960；逐页视觉抽样确认选择题、第 20 题和思维导图一致。"
            "新版本保留“共 8 页”页码及完整正式页眉，旧版为 5 页重排版，故替换为新版本。"
        ),
    },
    "temp-2024-数学-3056423645c4": {
        "source": "temp/版本2：数学（按省份分类）2008-2024/2008-2024·（山东）数学高考真题/2024年高考数学试卷（新课标Ⅰ卷）（空白卷）.pdf",
        "old_sha256": "3056423645c4bc35e8bf2ad96f431bed0f140865a5de1a96d75fcd760c549e7e",
        "new_sha256": "e241a28d4a53514825796a4d137a93dc5b56794b91c940ebd8e72bf8429ce2ce",
        "title": "2024年普通高等学校招生全国统一考试数学（新课标Ⅰ卷）",
        "paper_type": "新课标Ⅰ卷",
        "note": (
            "内容复核：与旧版视觉抽样比较，首页选择题及末页第 17–19 题一致；"
            "新版本保留正式页眉和“共 4 页”页码，旧版为无页眉的 3 页重排版，故替换为新版本。"
        ),
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def planned_replacements(rows: list[dict[str, str]]) -> list[tuple[dict[str, str], dict[str, str], Path, Path]]:
    by_id = {row["record_id"]: row for row in rows}
    plans = []
    for record_id, decision in REPLACEMENTS.items():
        row = by_id.get(record_id)
        if row is None:
            raise ValueError(f"replacement record not found: {record_id}")
        source = ROOT / decision["source"]
        destination = ROOT / row["local_path"]
        if not source.is_file() or not destination.is_file():
            raise FileNotFoundError(f"replacement files missing for {record_id}")
        current_hash = sha256(destination)
        if row.get("sha256") == decision["new_sha256"] and current_hash == decision["new_sha256"]:
            continue
        if row.get("sha256") != decision["old_sha256"] or current_hash != decision["old_sha256"]:
            raise ValueError(f"unexpected current hash for {record_id}")
        if sha256(source) != decision["new_sha256"]:
            raise ValueError(f"unexpected candidate hash for {record_id}")
        plans.append((row, decision, source, destination))
    return plans


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="replace reviewed files and update the catalog")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    plans = planned_replacements(rows)
    for row, _, source, destination in plans:
        print(f"{row['record_id']}: {source.relative_to(ROOT)} -> {destination.relative_to(ROOT)}")
    print(f"replacements={len(plans)} mode={'apply' if args.apply else 'dry-run'}")
    if not args.apply:
        return 0
    for row, decision, source, destination in plans:
        staged = destination.with_name(f".{destination.name}.temp-v2")
        shutil.copy2(source, staged)
        staged.replace(destination)
        row["sha256"] = decision["new_sha256"]
        row["title"] = decision["title"]
        row["paper_type"] = decision["paper_type"]
        row["source_url"] = f"local://{quote(decision['source'], safe='/')}"
        if decision["note"] not in row["notes"]:
            row["notes"] = f"{row['notes']}；{decision['note']}"
    with tempfile.NamedTemporaryFile("w", newline="", encoding="utf-8", dir=CATALOG.parent, delete=False) as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
        temporary = Path(handle.name)
    temporary.replace(CATALOG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
