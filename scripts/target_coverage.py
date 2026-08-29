#!/usr/bin/env python3
"""Validate declared paper-edition targets and render their coverage report."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from stats import ROOT, REGIONS, OFFICIAL_EVIDENCE, CATALOG, material_type, read_csv

TARGETS = ROOT / "data" / "paper-targets.csv"
REQUIRED_FIELDS = ("target_id", "year", "region", "subject", "paper_type", "title", "scope")


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def validate_targets(
    targets: list[dict[str, str]], record_ids: set[str], evidence_ids: set[str], region_codes: set[str]
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for number, row in enumerate(targets, start=2):
        missing = [field for field in REQUIRED_FIELDS if not row.get(field, "").strip()]
        if missing:
            errors.append(f"targets line {number}: missing {', '.join(missing)}")
        target_id = row.get("target_id", "").strip()
        if target_id in seen:
            errors.append(f"targets line {number}: duplicate target_id {target_id}")
        seen.add(target_id)
        try:
            if not 1977 <= int(row.get("year", "")) <= 2100:
                errors.append(f"targets line {number}: year out of range")
        except ValueError:
            errors.append(f"targets line {number}: year must be an integer")
        if row.get("region") not in region_codes | {"全国"}:
            errors.append(f"targets line {number}: unknown region")
        linked = split_ids(row.get("linked_record_ids", ""))
        if len(linked) != len(set(linked)):
            errors.append(f"targets line {number}: duplicate linked_record_id")
        for record_id in linked:
            if record_id not in record_ids:
                errors.append(f"targets line {number}: unknown linked_record_id {record_id}")
        for evidence_id in split_ids(row.get("official_evidence_ids", "")):
            if evidence_id not in evidence_ids:
                errors.append(f"targets line {number}: unknown official_evidence_id {evidence_id}")
    return errors


def target_state(target: dict[str, str], records_by_id: dict[str, dict[str, str]]) -> str:
    records = [records_by_id[item] for item in split_ids(target["linked_record_ids"])]
    complete = [
        row for row in records
        if row.get("status") != "withdrawn" and material_type(row) == "完整试卷"
    ]
    if any(row.get("availability") == "local" for row in complete):
        return "已入库"
    if complete:
        return "仅外部定位"
    return "待收录"


def summarize(targets: list[dict[str, str]], records_by_id: dict[str, dict[str, str]]) -> dict[str, object]:
    states = Counter(target_state(target, records_by_id) for target in targets)
    return {
        "total": len(targets),
        "states": states,
        "with_evidence": sum(bool(split_ids(target["official_evidence_ids"])) for target in targets),
        "by_year": Counter(target["year"] for target in targets),
        "by_subject": Counter(target["subject"] for target in targets),
    }


def render_markdown(
    targets: list[dict[str, str]], records_by_id: dict[str, dict[str, str]], region_names: dict[str, str]
) -> str:
    summary = summarize(targets, records_by_id)
    lines = [
        "# 卷制目标与缺口",
        "",
        "本页由 `python3 scripts/target_coverage.py --write docs/target-coverage.md` 自动生成。",
        "每项是一个实际可区分的考试卷制（年份、卷种、学科和使用范围），可关联多个文件版本。"
        "这里的覆盖率只针对 `data/paper-targets.csv` 中已明确声明的目标，**不能**代表全国所有高考试卷的完成率。",
        "",
        "## 已声明目标的覆盖情况",
        "",
        f"- 已声明目标：**{summary['total']}**",
        f"- 有官方身份佐证：**{summary['with_evidence']}**",
        f"- 已入库完整卷：**{summary['states'].get('已入库', 0)}**",
        f"- 仅外部定位：**{summary['states'].get('仅外部定位', 0)}**",
        f"- 待收录：**{summary['states'].get('待收录', 0)}**",
        "",
        "## 目标清单",
        "",
        "| 年份 | 地区 | 科目 | 卷种 | 目标 | 使用范围 | 入库状态 | 官方佐证 |",
        "| ---: | --- | --- | --- | --- | --- | --- | ---: |",
    ]
    ordered = sorted(targets, key=lambda target: (target["year"], target["region"], target["subject"], target["paper_type"]), reverse=True)
    for target in ordered:
        region = region_names.get(target["region"], target["region"])
        evidence_count = len(split_ids(target["official_evidence_ids"]))
        lines.append(
            f"| {target['year']} | {region} | {target['subject']} | {target['paper_type']} | "
            f"{target['title']} | {target['scope']} | {target_state(target, records_by_id)} | {evidence_count} |"
        )
    lines += [
        "",
        "> 当前目标清单以 2020 年全国一、二、三卷数学/理综物理，以及 2021 年全国甲乙卷数学/物理为经官方佐证的试点。后续应以官方公告、命题说明或可追溯使用范围逐年扩充，而不是从已有文件反推“应有卷数”。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate target data and exit")
    parser.add_argument("--write", metavar="PATH", help="write the target-coverage report")
    args = parser.parse_args()
    targets = read_csv(TARGETS)
    records = read_csv(CATALOG)
    evidence = read_csv(OFFICIAL_EVIDENCE)
    region_rows = read_csv(REGIONS)
    errors = validate_targets(
        targets,
        {row["record_id"] for row in records},
        {row["evidence_id"] for row in evidence},
        {row["code"] for row in region_rows},
    )
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            render_markdown(targets, {row["record_id"]: row for row in records}, {row["code"]: row["name"] for row in region_rows}),
            encoding="utf-8",
        )
    if args.check or not args.write:
        print(f"OK: {len(targets)} declared paper-edition targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
