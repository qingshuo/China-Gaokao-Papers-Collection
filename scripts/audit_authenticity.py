#!/usr/bin/env python3
"""Flag complete-paper records whose metadata resembles non-exam material."""

from __future__ import annotations

import argparse
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, ROOT, material_type, read_csv

SUSPICIOUS_TOKENS = (
    "模拟", "知识点", "专项", "专题", "练习", "预测", "押题", "名校", "诊断", "训练",
    "考点", "复习", "提分", "一模", "二模",
)


def suspicious_complete_papers(rows: list[dict[str, str]]) -> list[tuple[dict[str, str], list[str]]]:
    """Return only main-library records requiring human identity review."""
    findings: list[tuple[dict[str, str], list[str]]] = []
    for row in rows:
        if row.get("status") == "withdrawn" or material_type(row) != "完整试卷":
            continue
        metadata = " ".join((row.get("title", ""), row.get("notes", "")))
        matched = [token for token in SUSPICIOUS_TOKENS if token in metadata]
        if matched:
            findings.append((row, matched))
    return findings


def render_markdown(findings: list[tuple[dict[str, str], list[str]]]) -> str:
    lines = [
        "# 主试卷真实性观察", "",
        "本页由 `python3 scripts/audit_authenticity.py --write docs/authenticity-watch.md` 自动生成。",
        "筛查只根据标题和说明中的风险词生成候选，不能证明资料不是真题，也不会自动移除文件。答案、解析等附属资料不在此报告范围。", "",
        f"当前共有 **{len(findings)}** 条主试卷记录需要人工确认。", "",
    ]
    if findings:
        lines += ["| 年份 | 地区 | 科目 | 命中词 | 试卷 | 记录 ID |", "| ---: | --- | --- | --- | --- | --- |"]
        for row, matched in findings:
            title = row["title"].replace("|", "\\|")
            link = "../" + quote(row["local_path"], safe="/") if row.get("availability") == "local" else row["source_url"]
            lines.append(f"| {row['year']} | {row['region']} | {row['subject']} | {', '.join(matched)} | [{title}]({link}) | `{row['record_id']}` |")
        lines += ["", "> 请检查题目首页、考试名称、年份、题量和来源；确认是模拟/学习资料后，移入附属或片段资料，而非删除原始导入线索。", ""]
    else:
        lines += ["> 当前主试卷目录未命中模拟卷、知识点资料或专项练习等风险词。仍应以内容核验和可追溯来源为准。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the authenticity-watch report")
    args = parser.parse_args()
    findings = suspicious_complete_papers(read_csv(CATALOG))
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(findings), encoding="utf-8")
    print(f"suspicious_complete_papers={len(findings)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
