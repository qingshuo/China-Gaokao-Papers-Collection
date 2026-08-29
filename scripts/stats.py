#!/usr/bin/env python3
"""Validate the exam catalog and render a compact coverage report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
from collections import Counter
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "exams.csv"
SOURCES = ROOT / "data" / "sources.csv"
OFFICIAL_PORTALS = ROOT / "data" / "official-portals.csv"
OFFICIAL_EVIDENCE = ROOT / "data" / "official-evidence.csv"
REGIONS = ROOT / "config" / "regions.csv"

REQUIRED_FIELDS = (
    "record_id", "year", "region", "paper_type", "subject", "title",
    "source_url", "source_type", "license_status", "availability", "status",
    "notes",
)
STATUSES = {"planned", "discovered", "indexed", "verified", "withdrawn"}
AVAILABILITIES = {"none", "external", "local"}
MATERIAL_TYPES = {"完整试卷", "附属资料", "片段资料"}
PORTAL_STATUSES = {"pending_manual_check", "checked", "download_available", "announcement_only", "unavailable"}
EVIDENCE_TYPES = {"official_analysis", "official_announcement", "official_catalog", "official_download"}


def classify_material(row: dict[str, str]) -> str:
    """Classify a file for the main paper library or a supporting index."""
    title = row.get("title", "")
    paper_type = row.get("paper_type", "")
    if any(token in title for token in ("作文题目", "实验题", "部分试题", "压轴题", "单项选择题", "选择题汇编")):
        return "片段资料"
    if paper_type == "答案" and not any(token in title for token in ("无答案", "含答案")):
        return "附属资料"
    if paper_type in {"解析版", "试题答案解析"}:
        return "附属资料"
    return "完整试卷"


def material_type(row: dict[str, str]) -> str:
    return row.get("material_type") or classify_material(row)


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def file_format_error(path: Path) -> str | None:
    """Return an error when a common paper-file extension disagrees with its signature."""
    header = path.read_bytes()[:8]
    suffix = path.suffix.lower()
    if suffix == ".pdf" and not header.startswith(b"%PDF-"):
        return "PDF extension does not have a PDF signature"
    if suffix == ".docx" and not header.startswith(b"PK\x03\x04"):
        return "DOCX extension does not have an Office ZIP signature"
    return None


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
        category = row.get("material_type", "").strip()
        if category and category not in MATERIAL_TYPES:
            errors.append(f"line {number}: unknown material_type: {category}")
        digest = row.get("sha256", "").strip()
        if availability == "local" and not digest:
            errors.append(f"line {number}: local availability requires sha256")
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
                format_error = file_format_error(path)
                if format_error:
                    errors.append(f"line {number}: {format_error}: {row['local_path']}")
    return errors


def validate_official_portals(rows: list[dict[str, str]], region_codes: set[str]) -> list[str]:
    """Ensure the official-entry register has one usable row per covered area."""
    errors: list[str] = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        region = row.get("region", "").strip()
        if region not in region_codes | {"全国"}:
            errors.append(f"official portals line {number}: unknown region code: {region}")
        if region in seen:
            errors.append(f"official portals line {number}: duplicate region: {region}")
        seen.add(region)
        if not row.get("agency", "").strip() or not row.get("portal_url", "").startswith("http"):
            errors.append(f"official portals line {number}: agency and portal_url are required")
        status = row.get("portal_status", "").strip()
        if status not in PORTAL_STATUSES:
            errors.append(f"official portals line {number}: unknown portal_status: {status}")
    expected = region_codes | {"全国"}
    missing = expected - seen
    if missing:
        errors.append(f"official portals: missing regions: {', '.join(sorted(missing))}")
    return errors


def validate_official_evidence(rows: list[dict[str, str]], catalog_ids: set[str]) -> list[str]:
    """Validate official evidence without confusing it with a file's origin URL."""
    errors: list[str] = []
    seen: set[str] = set()
    for number, row in enumerate(rows, start=2):
        evidence_id = row.get("evidence_id", "").strip()
        if not evidence_id:
            errors.append(f"official evidence line {number}: missing evidence_id")
        elif evidence_id in seen:
            errors.append(f"official evidence line {number}: duplicate evidence_id {evidence_id}")
        seen.add(evidence_id)
        record_id = row.get("record_id", "").strip()
        if record_id not in catalog_ids:
            errors.append(f"official evidence line {number}: unknown record_id {record_id}")
        if row.get("evidence_type", "").strip() not in EVIDENCE_TYPES:
            errors.append(f"official evidence line {number}: unknown evidence_type")
        if not row.get("evidence_url", "").startswith("https://"):
            errors.append(f"official evidence line {number}: evidence_url must be an HTTPS URL")
        if not row.get("issuer", "").strip():
            errors.append(f"official evidence line {number}: missing issuer")
    return errors


def summarize(
    rows: list[dict[str, str]],
    source_rows: list[dict[str, str]],
    portal_rows: list[dict[str, str]] | None = None,
    evidence_rows: list[dict[str, str]] | None = None,
) -> dict[str, object]:
    active = [row for row in rows if row.get("status") != "withdrawn"]
    complete = [row for row in active if material_type(row) == "完整试卷"]
    return {
        "records": len(rows),
        "active_records": len(active),
        "complete_papers": len(complete),
        "supplementary_files": sum(material_type(row) == "附属资料" for row in active),
        "partial_files": sum(material_type(row) == "片段资料" for row in active),
        "verified": sum(row.get("status") == "verified" for row in complete),
        "local_files": sum(row.get("availability") == "local" for row in active),
        "years": sorted({row["year"] for row in complete if row.get("year")}),
        "regions": sorted({row["region"] for row in complete if row.get("region")}),
        "subjects": sorted({row["subject"] for row in complete if row.get("subject")}),
        "by_status": Counter(row.get("status", "") for row in complete),
        "by_year": Counter(row.get("year", "") for row in complete),
        "by_region": Counter(row.get("region", "") for row in complete),
        "by_subject": Counter(row.get("subject", "") for row in complete),
        "external_sources": len(source_rows),
        "official_portals": len(portal_rows or []),
        "portal_by_status": Counter(row.get("portal_status", "") for row in portal_rows or []),
        "official_evidence": len(evidence_rows or []),
        "official_evidence_records": len({row.get("record_id") for row in evidence_rows or []}),
    }


def render_markdown(summary: dict[str, object]) -> str:
    by_status = summary["by_status"]
    by_year = summary["by_year"]
    by_region = summary["by_region"]
    by_subject = summary["by_subject"]
    portal_by_status = summary["portal_by_status"]
    lines = [
        "# 覆盖统计",
        "",
        "本报告由 `python3 scripts/stats.py --write docs/coverage.md` 生成。主统计只计完整试卷；答案、解析和片段资料另列。",
        "",
        "## 总览",
        "",
        f"- 完整试卷：**{summary['complete_papers']}**",
        f"- 附属资料：**{summary['supplementary_files']}**；片段资料：**{summary['partial_files']}**",
        f"- 索引记录：**{summary['records']}**（有效记录 {summary['active_records']}，本地文件 {summary['local_files']}）",
        f"- 完整试卷中已核验：**{summary['verified']}**",
        f"- 已发现外部来源：**{summary['external_sources']}**",
        f"- 优先核查官方入口：**{summary['official_portals']}**（入口不等同于试卷下载或再发布许可）",
        f"- 已登记官方身份佐证：**{summary['official_evidence']}** 条，关联 **{summary['official_evidence_records']}** 份试卷（不等同于文件来源或许可）",
        f"- 覆盖年份：{', '.join(summary['years']) if summary['years'] else '暂无'}",
        f"- 覆盖省级区域：{', '.join(summary['regions']) if summary['regions'] else '暂无'}",
        "",
        "## 完整试卷按状态",
        "",
        "| 状态 | 数量 |",
        "| --- | ---: |",
    ]
    for status in sorted(STATUSES):
        lines.append(f"| {status} | {by_status.get(status, 0)} |")
    lines += [
        "", "## 官方入口核查进度", "",
        "此处衡量教育考试机构入口是否已核查；不代表这些站点提供试卷下载，也不代表试卷库覆盖率。", "",
        "| 入口状态 | 数量 |", "| --- | ---: |",
    ]
    lines += [f"| {status} | {portal_by_status.get(status, 0)} |" for status in sorted(PORTAL_STATUSES)]
    lines += ["", "## 完整试卷按年份", "", "| 年份 | 数量 |", "| ---: | ---: |"]
    lines += [f"| {year} | {by_year[year]} |" for year in sorted(by_year)] or ["| 暂无 | 0 |"]
    lines += ["", "## 完整试卷按区域", "", "| 区域 | 数量 |", "| --- | ---: |"]
    lines += [f"| {region} | {by_region[region]} |" for region in sorted(by_region)] or ["| 暂无 | 0 |"]
    lines += ["", "## 完整试卷按科目", "", "| 科目 | 数量 |", "| --- | ---: |"]
    lines += [f"| {subject} | {by_subject[subject]} |" for subject in sorted(by_subject)] or ["| 暂无 | 0 |"]
    lines += ["", "> 统计只反映本仓库 CSV 中的记录，不等同于全国试卷全集。", ""]
    return "\n".join(lines)


def render_readme(summary: dict[str, object]) -> str:
    """Render the repository landing page from the same catalog as the indexes."""
    by_year = summary["by_year"]
    by_subject = summary["by_subject"]
    years = sorted(by_year, reverse=True)
    subjects = sorted(by_subject)
    lines = [
        "# 中国高考试卷资料库",
        "",
        "按年份、学科和地区整理高考试卷。主库当前收录 "
        f"**{summary['complete_papers']} 份完整试卷**，覆盖 **{min(years)}-{max(years)} 年**；"
        "答案、解析和片段资料均单独归档，不混入主卷索引。",
        "",
        "**快速入口：** [按学科浏览](docs/papers-index.md) · [按年份浏览](docs/year-index.md) · "
        "[按地区浏览](docs/region-index.md) · [答案、解析与片段资料](docs/supplements-index.md) · "
        "[覆盖统计](docs/coverage.md) · [卷制目标与缺口](docs/target-coverage.md) · [官方渠道核查](docs/official-portals.md) · [来源可追溯性](docs/traceability.md) · [官方身份佐证](docs/official-evidence.md) · "
        "[内容审查记录](docs/content-review.md) · [候选重复核验队列](docs/candidate-duplicates.md) · [完全相同文件审计](docs/binary-duplicates.md) · "
        "[主试卷真实性观察](docs/authenticity-watch.md) · [PDF 完整性审计](docs/pdf-integrity.md) · "
        "[收集与核验计划](docs/collection-plan.md) · [项目说明](docs/project.md)",
        "",
        f"附属资料 **{summary['supplementary_files']} 份**、片段资料 **{summary['partial_files']} 份**已单独整理，"
        "不计入下方完整试卷统计。",
        "",
        "## 年份总览",
        "",
        "点击年份后，可打开当年所有学科、地区和卷种的完整试卷。",
        "",
        "| 年份 | 试卷数 | 查看索引 |",
        "| ---: | ---: | --- |",
    ]
    lines += [f"| {year} | {by_year[year]} | [{year} 年试卷](docs/year-index.md#{year}-年) |" for year in years]
    lines += [
        "",
        "## 学科入口",
        "",
        "| 学科 | 数量 | 索引 |",
        "| --- | ---: | --- |",
    ]
    lines += [f"| {subject} | {by_subject[subject]} | [查看](docs/papers-index.md#{subject}) |" for subject in subjects]
    lines += [
        "",
        "## 目录结构",
        "",
        "完整试卷放在 `papers/<年份>/<地区>/<学科>/`；答案、解析放在 `papers/supplements/`，"
        "片段资料放在 `papers/partials/`。PDF 可直接在线预览，DOCX/DOC 适合继续编辑。 "
        "每份文件的来源、SHA-256、格式、资料类别和授权状态记录在 [`data/exams.csv`](data/exams.csv)。",
        "",
        "本仓库只记录当前收集到的资料，不代表试卷全集。导入时会排除带推广、网盘或引流内容的文档；"
        "资料授权状态默认标记为“待核验”，使用和再分发前请查看 [第三方资料归属](THIRD-PARTY-NOTICES.md)。",
        "",
    ]
    return "\n".join(lines)


def render_papers_index(rows: list[dict[str, str]], region_names: dict[str, str]) -> str:
    active = [
        row for row in rows
        if row.get("status") != "withdrawn" and row.get("availability") == "local"
        and material_type(row) == "完整试卷"
    ]
    subjects = sorted({row["subject"] for row in active})
    lines = [
        "# 历年试卷索引",
        "",
        "本页由 `python3 scripts/stats.py --write-index docs/papers-index.md` 自动生成。",
        "",
        "## 按学科",
        "",
    ]
    for subject in subjects:
        count = sum(row["subject"] == subject for row in active)
        lines.append(f"- [{subject}（{count} 份）](#{subject})")
    for subject in subjects:
        lines += ["", f"## {subject}", ""]
        subject_years = sorted(
            {row["year"] for row in active if row["subject"] == subject},
            reverse=True,
        )
        lines += [" · ".join(f"[{year}](#{year}-{subject})" for year in subject_years), ""]
        for year in subject_years:
            matches = sorted(
                (row for row in active if row["year"] == year and row["subject"] == subject),
                key=lambda row: (row["region"], row["title"]),
            )
            lines += [
                f"### {year} {subject}", "",
                "| 试卷 | 地区 | 类型 | 格式 | 授权 |",
                "| --- | --- | --- | --- | --- |",
            ]
            for row in matches:
                target = "../" + quote(row["local_path"], safe="/")
                title = row["title"].replace("|", "\\|")
                region = region_names.get(row["region"], row["region"])
                if row["region"] == "全国" and "(" in row["title"]:
                    region = "全国/多省"
                extension = Path(row["local_path"]).suffix.lstrip(".").upper()
                license_label = "已声明" if row["license_status"] == "permitted" else "待核验"
                lines.append(
                    f"| [{title}]({target}) | {region} | {row['paper_type']} | {extension} | {license_label} |"
                )
            lines.append("")
    lines += ["> 返回 [README](../README.md) 查看年份总览。", ""]
    return "\n".join(lines)


def render_year_index(rows: list[dict[str, str]], region_names: dict[str, str]) -> str:
    """Render the complete-paper catalog grouped by year, then subject."""
    active = [
        row for row in rows
        if row.get("status") != "withdrawn" and row.get("availability") == "local"
        and material_type(row) == "完整试卷"
    ]
    years = sorted({row["year"] for row in active}, reverse=True)
    lines = [
        "# 按年份浏览", "",
        "本页由 `python3 scripts/stats.py --write-year-index docs/year-index.md` 自动生成。",
        "主索引只列完整试卷；答案、解析和片段资料见 [附属资料索引](supplements-index.md)。", "",
        "## 年份", "",
    ]
    for year in years:
        count = sum(row["year"] == year for row in active)
        lines.append(f"- [{year} 年（{count} 份）](#{year}年)")
    for year in years:
        lines += ["", f"## {year} 年", ""]
        subjects = sorted({row["subject"] for row in active if row["year"] == year})
        for subject in subjects:
            matches = sorted(
                (row for row in active if row["year"] == year and row["subject"] == subject),
                key=lambda row: (row["region"], row["title"]),
            )
            lines += [f"### {subject}（{len(matches)} 份）", "", "| 试卷 | 地区 | 类型 | 格式 | 授权 |", "| --- | --- | --- | --- | --- |"]
            for row in matches:
                target = "../" + quote(row["local_path"], safe="/")
                title = row["title"].replace("|", "\\|")
                region = region_names.get(row["region"], row["region"])
                extension = Path(row["local_path"]).suffix.lstrip(".").upper()
                license_label = "已声明" if row["license_status"] == "permitted" else "待核验"
                lines.append(f"| [{title}]({target}) | {region} | {row['paper_type']} | {extension} | {license_label} |")
            lines.append("")
    lines += ["> 返回 [README](../README.md) 或按 [地区浏览](region-index.md)。", ""]
    return "\n".join(lines)


def render_region_index(rows: list[dict[str, str]], region_names: dict[str, str]) -> str:
    """Render the complete-paper catalog grouped by region, then year."""
    active = [
        row for row in rows
        if row.get("status") != "withdrawn" and row.get("availability") == "local"
        and material_type(row) == "完整试卷"
    ]
    regions = sorted({row["region"] for row in active}, key=lambda code: region_names.get(code, code))
    lines = [
        "# 按地区浏览", "",
        "本页由 `python3 scripts/stats.py --write-region-index docs/region-index.md` 自动生成。",
        "全国统一卷与跨省共用卷标为“全国”；主索引只列完整试卷。", "",
        "## 地区", "",
    ]
    for region in regions:
        count = sum(row["region"] == region for row in active)
        name = region_names.get(region, region)
        lines.append(f"- [{name}（{count} 份）](#{name})")
    for region in regions:
        name = region_names.get(region, region)
        lines += ["", f"## {name}", ""]
        years = sorted({row["year"] for row in active if row["region"] == region}, reverse=True)
        for year in years:
            matches = sorted(
                (row for row in active if row["region"] == region and row["year"] == year),
                key=lambda row: (row["subject"], row["title"]),
            )
            lines += [f"### {year}（{len(matches)} 份）", "", "| 科目 | 试卷 | 类型 | 格式 | 授权 |", "| --- | --- | --- | --- | --- |"]
            for row in matches:
                target = "../" + quote(row["local_path"], safe="/")
                title = row["title"].replace("|", "\\|")
                extension = Path(row["local_path"]).suffix.lstrip(".").upper()
                license_label = "已声明" if row["license_status"] == "permitted" else "待核验"
                lines.append(f"| {row['subject']} | [{title}]({target}) | {row['paper_type']} | {extension} | {license_label} |")
            lines.append("")
    lines += ["> 返回 [README](../README.md) 或按 [年份浏览](year-index.md)。", ""]
    return "\n".join(lines)


def render_supplements_index(rows: list[dict[str, str]], region_names: dict[str, str]) -> str:
    active = [
        row for row in rows
        if row.get("status") != "withdrawn" and row.get("availability") == "local"
        and material_type(row) != "完整试卷"
    ]
    lines = [
        "# 附属资料索引", "",
        "本页收录答案、解析与片段资料；它们不计入主试卷库统计。",
    ]
    for category in ("附属资料", "片段资料"):
        matches = sorted(
            (row for row in active if material_type(row) == category),
            key=lambda row: (row["year"], row["subject"], row["region"], row["title"]),
            reverse=True,
        )
        lines += ["", f"## {category}（{len(matches)} 份）", "", "| 年份 | 科目 | 地区 | 资料 | 格式 |", "| ---: | --- | --- | --- | --- |"]
        for row in matches:
            target = "../" + quote(row["local_path"], safe="/")
            region = region_names.get(row["region"], row["region"])
            extension = Path(row["local_path"]).suffix.lstrip(".").upper()
            title = row["title"].replace("|", "\\|")
            lines.append(f"| {row['year']} | {row['subject']} | {region} | [{title}]({target}) | {extension} |")
    lines += ["", "> 返回 [README](../README.md) 查看完整试卷。", ""]
    return "\n".join(lines)


def render_official_evidence_index(
    evidence_rows: list[dict[str, str]], rows_by_id: dict[str, dict[str, str]], region_names: dict[str, str]
) -> str:
    """Render an audit trail for official identity evidence separate from source URLs."""
    labels = {
        "official_analysis": "官方试题评析",
        "official_announcement": "官方公告",
        "official_catalog": "官方目录",
        "official_download": "官方下载",
    }
    lines = [
        "# 官方身份佐证",
        "",
        "本页由 `python3 scripts/stats.py --write-official-evidence-index docs/official-evidence.md` 自动生成。",
        "官方身份佐证用于确认考试、卷种或命题背景；它**不替代**文件原始来源、内容逐页核验或再发布许可。",
        "",
        "| 年份 | 地区 | 科目 | 试卷 | 佐证类型 | 官方页面 |",
        "| ---: | --- | --- | --- | --- | --- |",
    ]
    ordered = sorted(
        evidence_rows,
        key=lambda item: (rows_by_id[item["record_id"]]["year"], item["record_id"], item["evidence_id"]),
        reverse=True,
    )
    for evidence in ordered:
        paper = rows_by_id[evidence["record_id"]]
        region = region_names.get(paper["region"], paper["region"])
        paper_title = paper["title"].replace("|", "\\|")
        target = "../" + quote(paper["local_path"], safe="/") if paper.get("availability") == "local" else paper["source_url"]
        evidence_label = labels[evidence["evidence_type"]]
        lines.append(
            f"| {paper['year']} | {region} | {paper['subject']} | [{paper_title}]({target}) | "
            f"{evidence_label} | [{evidence['issuer']}]({evidence['evidence_url']}) |"
        )
    lines += [
        "",
        "> 仅当官方页面实际指向同一考试/卷种时才可登记。若页面不提供原卷文件，主卷的来源与许可状态仍以 `data/exams.csv` 为准。",
        "",
    ]
    return "\n".join(lines)


def render_official_portals_index(portal_rows: list[dict[str, str]], region_names: dict[str, str]) -> str:
    """Render the official source-research queue for contributors."""
    status_labels = {
        "pending_manual_check": "待人工核查",
        "checked": "已核查",
        "download_available": "发现可下载文件",
        "announcement_only": "仅公告/评析",
        "unavailable": "入口不可用",
    }
    ordered = sorted(
        portal_rows,
        key=lambda row: (row["region"] != "全国", region_names.get(row["region"], row["region"])),
    )
    lines = [
        "# 官方渠道核查",
        "",
        "本页由 `python3 scripts/stats.py --write-official-portals-index docs/official-portals.md` 自动生成。",
        "每行是教育考试机构的优先核查入口，而非试卷文件来源；请在找到具体公告或文件后，将链接记录到 `data/exams.csv` 或 `data/official-evidence.csv`。",
        "",
        "| 地区 | 机构 | 入口 | 范围 | 状态 | 核查说明 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in ordered:
        region = region_names.get(row["region"], row["region"])
        status = status_labels[row["portal_status"]]
        notes = row["notes"].replace("|", "\\|")
        lines.append(
            f"| {region} | {row['agency']} | [访问入口]({row['portal_url']}) | {row['scope']} | {status} | {notes} |"
        )
    lines += [
        "",
        "> 核查时优先寻找原卷下载页、正式公告或试题评析；没有明确授权时，只登记链接和核验说明，不复制文件。",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate data and exit")
    parser.add_argument("--write", metavar="PATH", help="write the markdown report")
    parser.add_argument("--write-readme", metavar="PATH", help="write the repository landing-page index")
    parser.add_argument("--write-index", metavar="PATH", help="write the paper index")
    parser.add_argument("--write-year-index", metavar="PATH", help="write the year-first paper index")
    parser.add_argument("--write-region-index", metavar="PATH", help="write the region-first paper index")
    parser.add_argument("--write-supplements-index", metavar="PATH", help="write the supporting-material index")
    parser.add_argument("--write-official-evidence-index", metavar="PATH", help="write the official identity-evidence index")
    parser.add_argument("--write-official-portals-index", metavar="PATH", help="write the official source-research index")
    args = parser.parse_args()
    rows = read_csv(CATALOG)
    region_rows = read_csv(REGIONS)
    region_codes = {row["code"] for row in region_rows}
    errors = validate_catalog(rows, region_codes)
    portal_rows = read_csv(OFFICIAL_PORTALS)
    errors += validate_official_portals(portal_rows, region_codes)
    evidence_rows = read_csv(OFFICIAL_EVIDENCE)
    errors += validate_official_evidence(evidence_rows, {row["record_id"] for row in rows})
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    source_rows = read_csv(SOURCES)
    summary = summarize(rows, source_rows, portal_rows, evidence_rows)
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(summary), encoding="utf-8")
    if args.write_readme:
        output = Path(args.write_readme)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_readme(summary), encoding="utf-8")
    if args.write_index:
        output = Path(args.write_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        region_names = {row["code"]: row["name"] for row in region_rows}
        output.write_text(render_papers_index(rows, region_names), encoding="utf-8")
    if args.write_year_index:
        output = Path(args.write_year_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        region_names = {row["code"]: row["name"] for row in region_rows}
        output.write_text(render_year_index(rows, region_names), encoding="utf-8")
    if args.write_region_index:
        output = Path(args.write_region_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        region_names = {row["code"]: row["name"] for row in region_rows}
        output.write_text(render_region_index(rows, region_names), encoding="utf-8")
    if args.write_supplements_index:
        output = Path(args.write_supplements_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        region_names = {row["code"]: row["name"] for row in region_rows}
        output.write_text(render_supplements_index(rows, region_names), encoding="utf-8")
    if args.write_official_evidence_index:
        output = Path(args.write_official_evidence_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        region_names = {row["code"]: row["name"] for row in region_rows}
        rows_by_id = {row["record_id"]: row for row in rows}
        output.write_text(render_official_evidence_index(evidence_rows, rows_by_id, region_names), encoding="utf-8")
    if args.write_official_portals_index:
        output = Path(args.write_official_portals_index)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        region_names = {row["code"]: row["name"] for row in region_rows}
        output.write_text(render_official_portals_index(portal_rows, region_names), encoding="utf-8")
    if args.check or not (args.write or args.write_readme or args.write_index or args.write_year_index or args.write_region_index or args.write_supplements_index or args.write_official_evidence_index or args.write_official_portals_index):
        print(f"OK: {summary['records']} catalog records, {summary['external_sources']} external sources")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
