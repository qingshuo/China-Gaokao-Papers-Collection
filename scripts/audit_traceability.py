#!/usr/bin/env python3
"""Report whether complete-paper records have an externally traceable source."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, REGIONS, ROOT, material_type, read_csv


def source_scope(row: dict[str, str]) -> str:
    url = row.get("source_url", "")
    if url.startswith(("https://", "http://")):
        return "公开 URL"
    if url.startswith("local://"):
        return "仅本地导入来源"
    return "来源格式待修复"


def summarize(rows: list[dict[str, str]]) -> dict[str, Counter[str]]:
    complete = [row for row in rows if row.get("status") != "withdrawn" and material_type(row) == "完整试卷"]
    return {
        "source_scope": Counter(source_scope(row) for row in complete),
        "source_type": Counter(row.get("source_type", "") for row in complete),
        "license_status": Counter(row.get("license_status", "") for row in complete),
        "year_local_only": Counter(row["year"] for row in complete if source_scope(row) == "仅本地导入来源"),
        "subject_local_only": Counter(row.get("subject", "") for row in complete if source_scope(row) == "仅本地导入来源"),
    }


def render_markdown(rows: list[dict[str, str]]) -> str:
    summary = summarize(rows)
    complete = [row for row in rows if row.get("status") != "withdrawn" and material_type(row) == "完整试卷"]
    lines = [
        "# 来源可追溯性审计", "",
        "本页由 `python3 scripts/audit_traceability.py --write docs/traceability.md` 生成。",
        "“公开 URL”只表示记录可回到一个公开网页或文件地址；它**不表示**来源官方、文件正确或已获得再发布许可。", "",
        "## 总览", "",
        f"- 完整试卷记录：**{len(complete)}**",
        f"- 可回到公开 URL：**{summary['source_scope']['公开 URL']}**",
        f"- 仅记录本地导入来源：**{summary['source_scope']['仅本地导入来源']}**",
        f"- 来源格式待修复：**{summary['source_scope']['来源格式待修复']}**", "",
        "## 按来源形式", "", "| 来源形式 | 数量 |", "| --- | ---: |",
    ]
    for label, count in sorted(summary["source_scope"].items()):
        lines.append(f"| {label} | {count} |")
    lines += ["", "## 按授权状态", "", "| 授权状态 | 数量 |", "| --- | ---: |"]
    for label, count in sorted(summary["license_status"].items()):
        lines.append(f"| {label} | {count} |")
    lines += ["", "## 优先补公开出处的年份", "", "| 年份 | 仅本地导入来源的完整试卷 |", "| ---: | ---: |"]
    for year in sorted(summary["year_local_only"], reverse=True):
        lines.append(f"| {year} | {summary['year_local_only'][year]} |")
    lines += ["", "## 优先补公开出处的学科", "", "| 学科 | 仅本地导入来源的完整试卷 |", "| --- | ---: |"]
    for subject in sorted(summary["subject_local_only"]):
        lines.append(f"| {subject} | {summary['subject_local_only'][subject]} |")
    lines += ["", "## 使用方式", "", "优先为“仅本地导入来源”的记录补上具体官方公告页、公开文件地址或授权镜像地址；待补记录详见[本地来源补充队列](local-only-sources.md)。若无法确认可再发布性，应保留外部出处而非继续镜像。", ""]
    return "\n".join(lines)


def render_local_only_index(rows: list[dict[str, str]], region_names: dict[str, str]) -> str:
    """Render actionable source-remediation tasks without exposing local temp paths."""
    candidates = [
        row for row in rows
        if row.get("status") != "withdrawn" and material_type(row) == "完整试卷"
        and source_scope(row) == "仅本地导入来源"
    ]
    lines = [
        "# 本地来源补充队列", "",
        "本页由 `python3 scripts/audit_traceability.py --write-local-only-index docs/local-only-sources.md` 自动生成。",
        "这些记录已有仓库文件和 SHA-256，但原始出处仅记录为本地导入。请为每项补充可公开访问的官方公告、文件页或明确授权的镜像；没有可靠出处时，不应标为已核验。", "",
        f"当前共 **{len(candidates)}** 项，按年份倒序、学科和地区排序。", "",
        "| 年份 | 地区 | 科目 | 卷种 | 试卷 | 记录 ID |", "| ---: | --- | --- | --- | --- | --- |",
    ]
    for row in sorted(candidates, key=lambda item: (item["year"], item["subject"], item["region"], item["title"]), reverse=True):
        region = region_names.get(row["region"], row["region"])
        title = row["title"].replace("|", "\\|")
        path = "../" + quote(row["local_path"], safe="/")
        lines.append(f"| {row['year']} | {region} | {row['subject']} | {row['paper_type']} | [{title}]({path}) | `{row['record_id']}` |")
    lines += ["", "> 返回[来源可追溯性审计](traceability.md)。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the audit report")
    parser.add_argument("--write-local-only-index", metavar="PATH", help="write the local-source remediation queue")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(rows), encoding="utf-8")
    if args.write_local_only_index:
        output = Path(args.write_local_only_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        region_names = {row["code"]: row["name"] for row in read_csv(REGIONS)}
        output.write_text(render_local_only_index(rows, region_names), encoding="utf-8")
    summary = summarize(rows)
    print(f"public_urls={summary['source_scope']['公开 URL']} local_only={summary['source_scope']['仅本地导入来源']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
