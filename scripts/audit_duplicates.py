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
REGION_NAMES = frozenset((
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江", "上海", "江苏", "浙江", "安徽",
    "福建", "江西", "山东", "河南", "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
    "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆", "香港", "澳门", "台湾",
))


def without_region_list_annotations(title: str) -> str:
    """Remove parenthesized province lists, which duplicate the catalog's scope."""
    def replace(match: re.Match[str]) -> str:
        items = [item.strip().removesuffix("省").removesuffix("市") for item in re.split(r"[、,，]", match.group(1))]
        return "" if items and all(item in REGION_NAMES for item in items) else match.group(0)

    return re.sub(r"[（(]([^（）()]*)[）)]", replace, title)


def normalized_title(title: str) -> str:
    """Keep the identifying part of a title while ignoring presentation wording."""
    normalized = without_region_list_annotations(title).lower()
    for before, after in (("Ⅰ", "1"), ("ⅰ", "1"), ("Ⅱ", "2"), ("ⅱ", "2"), ("Ⅲ", "3"), ("ⅲ", "3"), ("理科", "理"), ("文科", "文")):
        normalized = normalized.replace(before, after)
    # Some imports use ASCII I/II/III while others use Arabic or Unicode
    # numerals for nationally named new-Gaokao paper sets.
    normalized = normalized.replace("新高考iii", "新高考3")
    normalized = normalized.replace("新高考ii", "新高考2")
    normalized = normalized.replace("新高考i", "新高考1")
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


def is_reviewed_conflict(group: list[dict[str, str]]) -> bool:
    """Return true only for a group whose every version was reviewed as a conflict.

    A title-normalization match is intentionally broad.  Once every member has
    an explicit content-review note saying it must not be merged, it is no
    longer actionable as a duplicate candidate and should be presented apart
    from the pending review queue.
    """
    return bool(group) and all(
        "内容复核：" in row.get("notes", "") and "暂不合并" in row.get("notes", "")
        for row in group
    )


def partition_groups(
    groups: list[tuple[tuple[str, str, str, str], list[dict[str, str]]]],
) -> tuple[list[tuple[tuple[str, str, str, str], list[dict[str, str]]]], list[tuple[tuple[str, str, str, str], list[dict[str, str]]]]]:
    """Return `(pending_candidates, reviewed_conflicts)` without hiding either."""
    pending = []
    reviewed = []
    for item in groups:
        (reviewed if is_reviewed_conflict(item[1]) else pending).append(item)
    return pending, reviewed


def render_group(group_key: tuple[str, str, str, str], group: list[dict[str, str]]) -> list[str]:
    year, region, subject, key = group_key
    lines = [f"### {year} · {region} · {subject} · `{key}`", "", "| 标题 | 类型 | 来源 | 文件 | SHA-256 |", "| --- | --- | --- | --- | --- |"]
    for row in sorted(group, key=lambda item: (item["title"], item["record_id"])):
        file_link = "—"
        if row.get("availability") == "local":
            file_link = f"[{Path(row['local_path']).name}](../{quote(row['local_path'], safe='/')})"
        title = row["title"].replace("|", "\\|")
        lines.append(f"| {title} | {row['paper_type']} | [{row['source_type']}]({row['source_url']}) | {file_link} | `{row['sha256'][:12]}` |")
    return lines + [""]


def render_markdown(groups: list[tuple[tuple[str, str, str, str], list[dict[str, str]]]]) -> str:
    pending, reviewed = partition_groups(groups)
    lines = [
        "# 候选重复核验队列", "",
        "本页由 `python3 scripts/audit_duplicates.py --write docs/candidate-duplicates.md` 生成。",
        "分组依据是同年份、地区、学科且标题规范化后一致；它只表示**候选重复**，不代表文件内容已经相同，不能据此自动删除。", "",
        f"待内容审查：**{len(pending)} 组**，涉及 **{sum(len(group) for _, group in pending)} 条**完整试卷记录。",
        f"已审查但存在实质冲突、暂不合并：**{len(reviewed)} 组**，涉及 **{sum(len(group) for _, group in reviewed)} 条完整试卷记录。", "",
    ]
    lines += ["## 待内容审查", ""]
    if pending:
        for group_key, group in pending:
            lines += render_group(group_key, group)
    else:
        lines += ["当前没有未处理的候选重复。", ""]
    lines += ["## 已审查的冲突版本", "", "这些版本已逐页比较并确认存在实质题干差异；保留全部版本，等待官方原卷或权威来源进一步核验。", ""]
    if reviewed:
        for group_key, group in reviewed:
            lines += render_group(group_key, group)
    else:
        lines += ["当前没有已审查的冲突版本。", ""]
    lines += ["> 对待内容审查的分组，应比较页数、题目内容、卷种范围和来源授权；确认同一试卷后再保留 PDF 或授权更清晰的版本。", ""]
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
