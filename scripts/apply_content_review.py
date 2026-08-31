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
    "deekur-2021-21-math",  # Same 22-question paper as the retained A4 original-layout version.
    "temp-2022-数学-fd1782d2496d",  # Same 新高考 I paper as the retained licensed GitHub version.
    "temp-2024-数学-3871d1b1134c",  # Same 2024 新高考 II paper as the retained licensed GitHub version.
    "temp-2024-数学-c2d8884979db",  # Same 2024 北京 paper as the retained licensed GitHub version.
}
# These actions were applied in the previous review commit. Keeping the IDs
# documents the provenance but must not make later review runs fail.
HISTORIC_REMOVED_IDS = {
    "temp-2023-物理-0a21a26edf23",
    "temp-2025-物理-1021d1a86165",
    "deekur-2025-53-math",
    "temp-2025-物理-69203d072e93",
    "temp-2025-物理-4f75fa4ef7ba",
    "temp-2025-物理-7b831f1303b3",
    "temp-2025-物理-19f9ce751abe",
    "temp-2025-物理-ac4daff519b4",
    "deekur-2021-21-math",
    "temp-2022-数学-fd1782d2496d",
    "temp-2024-数学-3871d1b1134c",
    "temp-2024-数学-c2d8884979db",
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
    "temp-2021-数学-cd8daafb088b",  # 2021 新高考 I 卷逐题答案解析，原卷另存。
    "temp-2022-数学-9bba412f6270",  # 全国甲卷文科：原卷重复，后附答案解析。
    "temp-2022-数学-29d6ee0acd18",  # 全国甲卷理科：原卷重复，后附答案解析。
}
TITLE_UPDATES = {
    "temp-2021-数学-698c99e83f2e": "2021年新高考I卷数学（原卷）",
    "temp-2021-数学-cd8daafb088b": "2021年新高考I卷数学（答案解析）",
    "temp-2022-数学-9bba412f6270": "2022年全国甲卷数学（文科）（答案解析）",
    "temp-2022-数学-29d6ee0acd18": "2022年全国甲卷数学（理科）（答案解析）",
}
TITLE_UPDATE_NOTES = {
    "temp-2021-数学-698c99e83f2e": "内容复核：已补全新高考I卷版本名称",
    "temp-2021-数学-cd8daafb088b": "内容复核：已补全新高考I卷版本名称",
    "temp-2022-数学-9bba412f6270": "内容复核：已更新标题为答案解析",
    "temp-2022-数学-29d6ee0acd18": "内容复核：已更新标题为答案解析",
}
RETAINED_NOTES = {
    "temp-2021-数学-698c99e83f2e": (
        "内容复核：与 deekur-2021-21-math 逐题一致，保留本文件作为更接近原卷的 A4 版；"
        "对应 A3 重排公开版本：https://raw.githubusercontent.com/deekur/gaokaomath/main/"
        "%E6%99%AE%E9%80%9A%E9%AB%98%E8%80%83/2021/2021%E6%96%B0%E9%AB%98%E8%80%831"
        "%28%E5%B1%B1%E4%B8%9C%2C%E5%B9%BF%E4%B8%9C%2C%E6%B9%96%E5%8D%97%2C%E6%B9%96%E5%8C%97"
        "%2C%E6%B2%B3%E5%8C%97%2C%E6%B1%9F%E8%8B%8F%2C%E7%A6%8F%E5%BB%BA%29.pdf；"
        "该公开版本的 CC-BY-4.0 声明不等同于本地导入文件的许可。"
    ),
    "deekur-2024-49-math": (
        "内容复核：与 temp-2024-数学-3871d1b1134c 的 1–19 题、题型分区、配图和题干逐项一致，"
        "两者均无答案；保留本文件，原因是来源可追溯且上游声明 CC-BY-4.0。"
    ),
    "deekur-2024-46-math": (
        "内容复核：与 temp-2024-数学-c2d8884979db 的 1–21 题、题型分区、配图和题干逐项一致，"
        "两者均无答案；保留本文件，原因是来源可追溯且上游声明 CC-BY-4.0。"
    ),
    "deekur-2024-43-math": (
        "上海市教育考试院已确认2024年普通高等学校招生全国统一文化考试上海数学卷制身份，"
        "且集合、函数、立体几何、气温与海水温度统计和体育锻炼时长统计题材与官方评析对应；"
        "同批次网络回忆版因题干差异已归入片段资料；官方评析不提供本地 PDF 的下载来源或再发布许可。"
    ),
}
PARTIAL_IDS = {
    "deekur-物理-2023-087",  # 上海物理重建版，声明部分图片可能偏差。
    "temp-2025-物理-d1cb17271a18",  # One-page 四川卷回忆版，仅含第 14、15 题。
    "temp-2024-物理-e538a406533b",  # 上海物理网络回忆版。
    "temp-2024-数学-408b18cc7007",  # 上海数学网络回忆版，正式版本另存。
    "temp-2025-化学-32b48f865ec7",  # 上海化学回忆整合版，含缺失信息和答案。
}
PARTIAL_REASONS = {
    "deekur-物理-2023-087": (
        "内容复核：文件首页注明“图片能确定的只有第17、20题，其余图片可能会有偏差”；"
        "不能作为可确认的正式完整原卷。"
    ),
    "temp-2024-物理-e538a406533b": (
        "内容复核：文件首页明确标注“网络回忆版”；不能作为正式完整原卷。"
    ),
    "temp-2024-数学-408b18cc7007": (
        "内容复核：文件首页明确标注“网络回忆版”，且第 8、11 题与保留的正式卷制版本存在实质题干差异；"
        "不能作为可确认的正式完整原卷。"
    ),
    "temp-2025-化学-32b48f865ec7": (
        "内容复核：文件首页标注“回忆版”，多处题注说明根据回忆和文献资料整合，"
        "且后附参考答案、存在题目信息缺失；不能作为正式完整原卷。"
    ),
}
CONFLICTS = {
    "2024-全国-数学-新高考I卷": "内容复核：与 deekur-2024-48-math 的题号、分区及绝大多数题干一致，但第 9 题缺少一条背景句，暂不合并，待官方原卷核验。",
    "deekur-2024-48-math": "内容复核：与 2024-全国-数学-新高考I卷 的题号、分区及绝大多数题干一致，但第 9 题多出一条背景句，暂不合并，待官方原卷核验。",
    "deekur-2026-58-math": "内容复核：与 temp-2026-数学-b4cda6722b5f 存在实质题干差异，暂不合并，待官方来源核验。",
    "temp-2026-数学-b4cda6722b5f": "内容复核：与 deekur-2026-58-math 存在实质题干差异，暂不合并，待官方来源核验。",
    "deekur-2026-55-math": "内容复核：与 temp-2026-数学-66df94475d50 存在实质题干差异，暂不合并，待官方来源核验。",
    "temp-2026-数学-66df94475d50": "内容复核：与 deekur-2026-55-math 存在实质题干差异，暂不合并，待官方来源核验。",
    "deekur-2026-59-math": "内容复核：与 temp-2026-数学-9c9cb50bcd0c 存在实质题干差异，暂不合并，待官方来源核验。",
    "temp-2026-数学-9c9cb50bcd0c": "内容复核：与 deekur-2026-59-math 存在实质题干差异，暂不合并，待官方来源核验。",
    "deekur-2024-47-math": "内容复核：与 temp-2024-数学-d7ffc6dab1af 存在实质题干差异，暂不合并，待官方原卷核验。",
    "temp-2024-数学-d7ffc6dab1af": "内容复核：与 deekur-2024-47-math 存在实质题干差异，暂不合并，待官方原卷核验。",
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
    expected_ids = (REMOVE_IDS - HISTORIC_REMOVED_IDS) | SUPPLEMENT_IDS | PARTIAL_IDS | set(CONFLICTS) | set(TITLE_UPDATES) | set(RETAINED_NOTES)
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
        if source != destination:
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
        reason = PARTIAL_REASONS.get(row["record_id"], "")
        row["notes"] = f"{row['notes']}；内容复核后归类为{row['material_type']}"
        if reason and reason not in row["notes"]:
            row["notes"] = f"{row['notes']}；{reason}"
    for row in rows:
        if row["record_id"] in TITLE_UPDATES:
            row["title"] = TITLE_UPDATES[row["record_id"]]
            title_note = TITLE_UPDATE_NOTES[row["record_id"]]
            legacy_note = "内容复核：已补全新高考I卷版本名称"
            if row["record_id"].startswith("temp-2022-") and legacy_note in row["notes"]:
                row["notes"] = row["notes"].replace(legacy_note, title_note)
            elif title_note not in row["notes"]:
                row["notes"] = f"{row['notes']}；{title_note}"
    for row in rows:
        if row["record_id"] in CONFLICTS and CONFLICTS[row["record_id"]] not in row["notes"]:
            row["notes"] = f"{row['notes']}；{CONFLICTS[row['record_id']]}"
        if row["record_id"] in RETAINED_NOTES and RETAINED_NOTES[row["record_id"]] not in row["notes"]:
            row["notes"] = f"{row['notes']}；{RETAINED_NOTES[row['record_id']]}"
    rows = [row for row in rows if row["record_id"] not in remove_ids]
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
