#!/usr/bin/env python3
"""Validate and render community-sourced paper-usage leads without treating them as official evidence."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from stats import ROOT, read_csv

LEADS = ROOT / "data" / "usage-scope-leads.csv"
REQUIRED_FIELDS = ("lead_id", "year", "subject", "paper_type", "scope", "source_name", "source_url", "confidence", "notes")
CONFIDENCE = {"community_unverified"}


def validate_leads(rows: list[dict[str, str]]) -> list[str]:
    """Keep community usage data explicitly separate from official evidence."""
    errors: list[str] = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        missing = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
        if missing:
            errors.append(f"usage leads line {number}: missing {', '.join(missing)}")
        lead_id = row.get("lead_id", "").strip()
        if lead_id in seen:
            errors.append(f"usage leads line {number}: duplicate lead_id {lead_id}")
        seen.add(lead_id)
        try:
            if not 1977 <= int(row.get("year", "")) <= 2100:
                errors.append(f"usage leads line {number}: year out of range")
        except ValueError:
            errors.append(f"usage leads line {number}: year must be an integer")
        if row.get("confidence", "") not in CONFIDENCE:
            errors.append(f"usage leads line {number}: unknown confidence")
        if not row.get("source_url", "").startswith("https://"):
            errors.append(f"usage leads line {number}: source_url must be an HTTPS URL")
    return errors


def render_markdown(rows: list[dict[str, str]]) -> str:
    """Render a target-discovery queue, deliberately not a coverage claim."""
    by_year = Counter(row["year"] for row in rows)
    lines = [
        "# 用卷范围线索",
        "",
        "本页由 `python3 scripts/usage_scope_leads.py --write docs/usage-scope-leads.md` 自动生成。",
        "这些记录来自社区维护的用卷范围表，用于发现应核查的卷制、辅助按省份导航；**不是官方身份佐证、试卷文件来源或再发布许可**。",
        "",
        "## 当前线索规模",
        "",
        f"- 已登记线索：**{len(rows)}** 条",
        f"- 涉及年份：{', '.join(sorted(by_year, reverse=True)) or '暂无'}",
        "- 可信级别：均为 `community_unverified`，必须以教育考试机构原始公告、下载页或试题评析复核后，才能进入 `paper-targets.csv` 的官方佐证目标。",
        "",
        "## 卷制线索",
        "",
        "| 年份 | 学科 | 卷种 | 声称使用范围 | 社区来源 | 状态 | 说明 |",
        "| ---: | --- | --- | --- | --- | --- | --- |",
    ]
    for row in sorted(rows, key=lambda item: (item["year"], item["subject"], item["paper_type"]), reverse=True):
        notes = row["notes"].replace("|", "\\|")
        lines.append(
            f"| {row['year']} | {row['subject']} | {row['paper_type']} | {row['scope']} | "
            f"[{row['source_name']}]({row['source_url']}) | 社区待核验 | {notes} |"
        )
    lines += [
        "",
        "> 实际收录以 `data/exams.csv` 为准；目标完成率只以 `data/paper-targets.csv` 中经官方佐证的目标计算。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate usage-scope leads and exit")
    parser.add_argument("--write", metavar="PATH", help="write the usage-scope lead index")
    args = parser.parse_args()
    rows = read_csv(LEADS)
    errors = validate_leads(rows)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(rows), encoding="utf-8")
    if args.check or not args.write:
        print(f"OK: {len(rows)} community usage-scope leads")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
