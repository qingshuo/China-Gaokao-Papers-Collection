#!/usr/bin/env python3
"""Report likely duplicate complete papers without changing the catalog."""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, ROOT, material_type

REMOVABLE_TITLE_TOKENS = (
    "普通高等学校招生全国统一考试", "普通高中学业水平选择性考试", "普通高校招生选考",
    "普通高考", "高考", "真题", "试卷", "试题", "文档版", "网络收集版",
    "原卷版", "原卷", "无答案", "含答案",
)
SUBJECT_TOKENS = ("数学", "物理", "化学", "生物", "地理", "历史", "政治", "语文", "英语", "日语")


def normalized_title(title: str) -> str:
    """Keep the identifying part of a title while ignoring presentation wording."""
    normalized = title.lower()
    for before, after in (("Ⅰ", "1"), ("ⅰ", "1"), ("Ⅱ", "2"), ("ⅱ", "2"), ("Ⅲ", "3"), ("ⅲ", "3"), ("理科", "理"), ("文科", "文")):
        normalized = normalized.replace(before, after)
    normalized = re.sub(r"(?:19|20)\d{2}年?", "", normalized)
    for token in REMOVABLE_TITLE_TOKENS + SUBJECT_TOKENS:
        normalized = normalized.replace(token, "")
    return re.sub(r"[^\w\u4e00-\u9fff]", "", normalized).replace("卷", "")


def candidate_groups(rows: list[dict[str, str]]) -> list[tuple[tuple[str, str, str, str], list[dict[str, str]]]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("status") == "withdrawn" or material_type(row) != "完整试卷":
            continue
        key = (row["year"], row["region"], row["subject"], normalized_title(row["title"]))
        if key[-1]:
            groups[key].append(row)
    return sorted((key, group) for key, group in groups.items() if len(group) > 1)


def render_markdown(groups: list[tuple[tuple[str, str, str, str], list[dict[str, str]]]]) -> str:
    lines = [
        "# 候选重复核验队列", "",
        "本页由 `python3 scripts/audit_duplicates.py --write docs/candidate-duplicates.md` 生成。",
        "分组依据是同年份、地区、学科且标题规范化后一致；它只表示**候选重复**，不代表文件内容已经相同，不能据此自动删除。", "",
        f"当前共有 **{len(groups)} 组**候选，涉及 **{sum(len(group) for _, group in groups)} 条**完整试卷记录。", "",
    ]
    for (year, region, subject, key), group in groups:
        lines += [f"## {year} · {region} · {subject} · `{key}`", "", "| 标题 | 类型 | 来源 | 文件 | SHA-256 |", "| --- | --- | --- | --- | --- |"]
        for row in sorted(group, key=lambda item: (item["title"], item["record_id"])):
            file_link = "—"
            if row.get("availability") == "local":
                file_link = f"[{Path(row['local_path']).name}](../{quote(row['local_path'], safe='/')})"
            title = row["title"].replace("|", "\\|")
            lines.append(f"| {title} | {row['paper_type']} | [{row['source_type']}]({row['source_url']}) | {file_link} | `{row['sha256'][:12]}` |")
        lines.append("")
    lines += ["> 复核应比较页数、题目内容、卷种范围和来源授权；确认同一试卷后再保留 PDF 或授权更清晰的版本。", ""]
    return "\n".join(lines)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the audit report")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    groups = candidate_groups(rows)
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(groups), encoding="utf-8")
    print(f"candidate_groups={len(groups)} records={sum(len(group) for _, group in groups)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
