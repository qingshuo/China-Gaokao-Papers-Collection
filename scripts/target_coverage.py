#!/usr/bin/env python3
"""Validate declared paper-edition targets and render their coverage report."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from stats import EVIDENCE_TYPES, IDENTITY_SCOPES, ROOT, REGIONS, OFFICIAL_EVIDENCE, CATALOG, material_type, read_csv

TARGETS = ROOT / "data" / "paper-targets.csv"
TARGET_EVIDENCE = ROOT / "data" / "target-evidence.csv"
REQUIRED_FIELDS = ("target_id", "year", "region", "subject", "paper_type", "title", "scope")


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(";") if item.strip()]


def validate_target_evidence(rows: list[dict[str, str]], target_ids: set[str]) -> list[str]:
    """Validate target-level official evidence when no paper file is available yet."""
    errors: list[str] = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        evidence_id = row.get("evidence_id", "").strip()
        if not evidence_id:
            errors.append(f"target evidence line {number}: missing evidence_id")
        elif evidence_id in seen:
            errors.append(f"target evidence line {number}: duplicate evidence_id")
        seen.add(evidence_id)
        if row.get("target_id", "").strip() not in target_ids:
            errors.append(f"target evidence line {number}: unknown target_id {row.get('target_id', '')}")
        if row.get("evidence_type", "").strip() not in EVIDENCE_TYPES:
            errors.append(f"target evidence line {number}: unknown evidence_type")
        if row.get("identity_scope", "").strip() != "full_target":
            errors.append(f"target evidence line {number}: identity_scope must be full_target")
        if not row.get("evidence_url", "").startswith("https://"):
            errors.append(f"target evidence line {number}: evidence_url must be an HTTPS URL")
        if not row.get("issuer", "").strip():
            errors.append(f"target evidence line {number}: missing issuer")
    return errors


def validate_targets(
    targets: list[dict[str, str]], records_by_id: dict[str, dict[str, str]], evidence_by_id: dict[str, dict[str, str]],
    region_codes: set[str], target_evidence_by_id: dict[str, dict[str, str]] | None = None
) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    target_evidence_by_id = target_evidence_by_id or {}
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
            if record_id not in records_by_id:
                errors.append(f"targets line {number}: unknown linked_record_id {record_id}")
                continue
            record = records_by_id[record_id]
            for field in ("year", "region", "subject"):
                if record.get(field) != row.get(field):
                    errors.append(f"targets line {number}: linked_record_id {record_id} has a different {field}")
        for evidence_id in split_ids(row.get("official_evidence_ids", "")):
            if evidence_id in evidence_by_id:
                if evidence_by_id[evidence_id].get("record_id") not in linked:
                    errors.append(f"targets line {number}: official_evidence_id {evidence_id} is not linked to this target's record")
                if evidence_by_id[evidence_id].get("identity_scope") != "full_target":
                    errors.append(f"targets line {number}: official_evidence_id {evidence_id} is not full-target identity evidence")
            elif evidence_id in target_evidence_by_id:
                if target_evidence_by_id[evidence_id].get("target_id") != target_id:
                    errors.append(f"targets line {number}: official_evidence_id {evidence_id} belongs to another target")
            else:
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
        "> 当前目标清单以 2017–2020 年全国一、二、三卷数学（并含 2020 年理综物理）、2021 年全国甲乙卷数学/物理及 2024 年上海春考数学为经官方佐证的试点。后续应以官方公告、命题说明或可追溯使用范围逐年扩充，而不是从已有文件反推“应有卷数”。",
        "",
    ]
    return "\n".join(lines)


def render_target_evidence_index(target_evidence: list[dict[str, str]], targets_by_id: dict[str, dict[str, str]], region_names: dict[str, str]) -> str:
    """Render official evidence that establishes a target before its PDF is found."""
    labels = {
        "official_analysis": "官方试题评析",
        "official_announcement": "官方公告",
        "official_catalog": "官方目录",
        "official_download": "官方下载",
    }
    lines = [
        "# 官方卷制佐证",
        "",
        "本页由 `python3 scripts/target_coverage.py --write-evidence-index docs/target-evidence.md` 自动生成。",
        "这些页面均已标记为“完整卷制身份”，用于确认一个卷制目标真实存在，尤其适用于尚未找到原卷文件的项目；它们**不等同于**试卷文件来源、逐页内容核验或再发布许可。",
        "",
        "| 年份 | 地区 | 学科 | 卷制目标 | 佐证类型 | 官方页面 |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    for evidence in sorted(target_evidence, key=lambda row: (targets_by_id[row["target_id"]]["year"], row["target_id"]), reverse=True):
        target = targets_by_id[evidence["target_id"]]
        region = region_names.get(target["region"], target["region"])
        lines.append(
            f"| {target['year']} | {region} | {target['subject']} | {target['title']} | {labels[evidence['evidence_type']]} | "
            f"[{evidence['issuer']}]({evidence['evidence_url']}) |"
        )
    lines += [
        "",
        "> 原卷下载、清晰许可或可验证镜像仍需单独记录到 `data/exams.csv`；在此之前，目标状态应保持“待收录”。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate target data and exit")
    parser.add_argument("--write", metavar="PATH", help="write the target-coverage report")
    parser.add_argument("--write-evidence-index", metavar="PATH", help="write the target-level official evidence index")
    args = parser.parse_args()
    targets = read_csv(TARGETS)
    records = read_csv(CATALOG)
    evidence = read_csv(OFFICIAL_EVIDENCE)
    target_evidence = read_csv(TARGET_EVIDENCE)
    region_rows = read_csv(REGIONS)
    records_by_id = {row["record_id"]: row for row in records}
    evidence_by_id = {row["evidence_id"]: row for row in evidence}
    targets_by_id = {row["target_id"]: row for row in targets}
    target_evidence_by_id = {row["evidence_id"]: row for row in target_evidence}
    errors = validate_target_evidence(target_evidence, set(targets_by_id))
    errors += validate_targets(targets, records_by_id, evidence_by_id, {row["code"] for row in region_rows}, target_evidence_by_id)
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
            render_markdown(targets, records_by_id, {row["code"]: row["name"] for row in region_rows}),
            encoding="utf-8",
        )
    if args.write_evidence_index:
        output = Path(args.write_evidence_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            render_target_evidence_index(target_evidence, targets_by_id, {row["code"]: row["name"] for row in region_rows}),
            encoding="utf-8",
        )
    if args.check or not (args.write or args.write_evidence_index):
        print(f"OK: {len(targets)} declared paper-edition targets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
