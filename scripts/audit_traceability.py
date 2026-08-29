#!/usr/bin/env python3
"""Report whether complete-paper records have an externally traceable source."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from stats import CATALOG, ROOT, material_type


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
    lines += ["", "## 使用方式", "", "优先为“仅本地导入来源”的记录补上具体官方公告页、公开文件地址或授权镜像地址；若无法确认可再发布性，应保留外部出处而非继续镜像。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the audit report")
    args = parser.parse_args()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(rows), encoding="utf-8")
    summary = summarize(rows)
    print(f"public_urls={summary['source_scope']['公开 URL']} local_only={summary['source_scope']['仅本地导入来源']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
