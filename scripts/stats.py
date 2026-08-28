#!/usr/bin/env python3
"""Validate the exam catalog and render a compact coverage report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "exams.csv"
SOURCES = ROOT / "data" / "sources.csv"
REGIONS = ROOT / "config" / "regions.csv"

REQUIRED_FIELDS = (
    "record_id", "year", "region", "paper_type", "subject", "title",
    "source_url", "source_type", "license_status", "availability", "status",
    "sha256", "notes",
)
STATUSES = {"planned", "discovered", "indexed", "verified", "withdrawn"}
AVAILABILITIES = {"none", "external", "local"}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def validate_catalog(rows: list[dict[str, str]], region_codes: set[str]) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        missing = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
        if missing:
            errors.append(f"line {number}: missing {', '.join(missing)}")
        record_id = row.get("record_id", "").strip()
        if record_id and record_id in seen:
            errors.append(f"line {number}: duplicate record_id {record_id}")
        seen.add(record_id)
        try:
            year = int(row.get("year", ""))
            if not 1977 <= year <= 2100:
                errors.append(f"line {number}: year out of range: {year}")
        except ValueError:
            errors.append(f"line {number}: year must be an integer")
        region = row.get("region", "").strip()
        if region and region != "全国" and region not in region_codes:
            errors.append(f"line {number}: unknown region code: {region}")
        status = row.get("status", "").strip()
        if status and status not in STATUSES:
            errors.append(f"line {number}: unknown status: {status}")
        availability = row.get("availability", "").strip()
        if availability and availability not in AVAILABILITIES:
            errors.append(f"line {number}: unknown availability: {availability}")
        if availability == "local" and not row.get("local_path", "").strip():
            errors.append(f"line {number}: local availability requires local_path")
        if availability != "local" and row.get("local_path", "").strip():
            errors.append(f"line {number}: local_path is only valid for local availability")
        digest = row.get("sha256", "").strip()
        if digest and not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            errors.append(f"line {number}: sha256 must be 64 hexadecimal characters")
        if availability == "local" and digest:
            path = ROOT / row["local_path"].strip()
            if not path.is_file():
                errors.append(f"line {number}: local file not found: {row['local_path']}")
            else:
                actual = hashlib.sha256(path.read_bytes()).hexdigest()
                if actual.lower() != digest.lower():
                    errors.append(f"line {number}: sha256 mismatch for {row['local_path']}")
    return errors


def summarize(rows: list[dict[str, str]], source_rows: list[dict[str, str]]) -> dict[str, object]:
    active = [row for row in rows if row.get("status") != "withdrawn"]
    return {
        "records": len(rows),
        "active_records": len(active),
        "verified": sum(row.get("status") == "verified" for row in active),
        "local_files": sum(row.get("availability") == "local" for row in active),
        "years": sorted({row["year"] for row in active if row.get("year")}),
        "regions": sorted({row["region"] for row in active if row.get("region")}),
        "subjects": sorted({row["subject"] for row in active if row.get("subject")}),
        "by_status": Counter(row.get("status", "") for row in active),
        "by_year": Counter(row.get("year", "") for row in active),
        "by_region": Counter(row.get("region", "") for row in active),
        "by_subject": Counter(row.get("subject", "") for row in active),
        "external_sources": len(source_rows),
    }


def render_markdown(summary: dict[str, object]) -> str:
    by_status = summary["by_status"]
    by_year = summary["by_year"]
    by_region = summary["by_region"]
    by_subject = summary["by_subject"]
    lines = [
        "# 覆盖统计",
        "",
        "本报告由 `python3 scripts/stats.py --write docs/coverage.md` 生成。撤回记录不计入覆盖统计。",
        "",
        "## 总览",
        "",
        f"- 索引记录：**{summary['records']}**（有效记录 {summary['active_records']}）",
        f"- 已核验：**{summary['verified']}**",
        f"- 仓库本地文件：**{summary['local_files']}**",
        f"- 已发现外部来源：**{summary['external_sources']}**",
        f"- 覆盖年份：{', '.join(summary['years']) if summary['years'] else '暂无'}",
        f"- 覆盖省级区域：{', '.join(summary['regions']) if summary['regions'] else '暂无'}",
        "",
        "## 按状态",
        "",
        "| 状态 | 数量 |",
        "| --- | ---: |",
    ]
    for status in sorted(STATUSES):
        lines.append(f"| {status} | {by_status.get(status, 0)} |")
    lines += ["", "## 按年份", "", "| 年份 | 数量 |", "| ---: | ---: |"]
    lines += [f"| {year} | {by_year[year]} |" for year in sorted(by_year)] or ["| 暂无 | 0 |"]
    lines += ["", "## 按区域", "", "| 区域 | 数量 |", "| --- | ---: |"]
    lines += [f"| {region} | {by_region[region]} |" for region in sorted(by_region)] or ["| 暂无 | 0 |"]
    lines += ["", "## 按科目", "", "| 科目 | 数量 |", "| --- | ---: |"]
    lines += [f"| {subject} | {by_subject[subject]} |" for subject in sorted(by_subject)] or ["| 暂无 | 0 |"]
    lines += ["", "> 统计只反映本仓库 CSV 中的记录，不等同于全国试卷全集。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate data and exit")
    parser.add_argument("--write", metavar="PATH", help="write the markdown report")
    args = parser.parse_args()
    rows = read_csv(CATALOG)
    region_codes = {row["code"] for row in read_csv(REGIONS)}
    errors = validate_catalog(rows, region_codes)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    source_rows = read_csv(SOURCES)
    summary = summarize(rows, source_rows)
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(summary), encoding="utf-8")
    if args.check or not args.write:
        print(f"OK: {summary['records']} catalog records, {summary['external_sources']} external sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
