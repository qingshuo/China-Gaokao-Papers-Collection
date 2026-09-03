#!/usr/bin/env python3
"""Audit the 2008-2024 province-organized temp collection without importing it.

The provider sorted files by the provinces that used them.  That is useful
coverage information, but not proof of a paper's issuing scope: a national
paper can occur under dozens of province directories.  This report preserves
the original path and deliberately keeps those two ideas separate.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from stats import CATALOG, ROOT, material_type, read_csv

TEMP_ROOT = ROOT / "temp"
DEFAULT_COLLECTION = "版本2："
ROMAN = str.maketrans({"Ⅰ": "1", "Ⅱ": "2", "Ⅲ": "3", "Ⅳ": "4", "ⅰ": "1", "ⅱ": "2", "ⅲ": "3", "ⅳ": "4"})
REGIONS = tuple(read_csv(ROOT / "config" / "regions.csv"))
REGION_CODE = {row["name"]: row["code"] for row in REGIONS}
REGION_ORDER = {row["code"]: number for number, row in enumerate(REGIONS)}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalized(text: str) -> str:
    return re.sub(r"[（）()\[\]【】\s·—_-]", "", text.translate(ROMAN)).lower()


def track(text: str) -> str:
    if re.search(r"[（(]理(?:科)?[）)]", text) or "理科" in text:
        return "理"
    if re.search(r"[（(]文(?:科)?[）)]", text) or "文科" in text:
        return "文"
    # Catalog titles often use a compact trailing 文/理 marker (for example
    # ``2015全国1理``).  Do not treat the 文 in “语文” as such a marker.
    compact = normalized(text.replace("语文", "").replace("文综", ""))
    if compact.endswith("理"):
        return "理"
    if compact.endswith("文"):
        return "文"
    return ""


def extract_year(text: str) -> str:
    match = re.search(r"(?:19|20)\d{2}", text)
    return match.group(0) if match else ""


def subject_from_path(path: Path) -> str:
    for parent in path.parents:
        match = re.search(r"版本2：([^（(]+)", parent.name)
        if match:
            return match.group(1).strip()
    return ""


def directory_region(path: Path) -> str:
    for parent in path.parents:
        match = re.search(r"[（(]([^）)]+)[）)]", parent.name)
        if match and match.group(1) in REGION_CODE:
            return REGION_CODE[match.group(1)]
    return ""


def named_regions(text: str) -> list[str]:
    return [code for name, code in REGION_CODE.items() if name in text]


def paper_family(text: str, year: str) -> str:
    """Return a stable family only when the displayed title identifies one."""
    compact = normalized(text)
    if "春考" in compact or "春季高考" in compact:
        return "春考"
    if "秋考" in compact or "秋季高考" in compact:
        return "秋考"
    month = re.search(r"浙江(1[01]|[1-9])月", compact)
    if month:
        return f"浙江{month.group(1)}月卷"
    if "全国甲" in compact or "甲卷" in compact:
        return "全国甲卷"
    if "全国乙" in compact or "乙卷" in compact:
        return "全国乙卷"
    for prefix, label in (("新高考", "新高考"), ("新课标", "新课标"), ("全国卷", "全国"), ("全国", "全国"), ("大纲版", "大纲版")):
        match = re.search(prefix + r"([123])(?:卷)?", compact)
        if match:
            number = match.group(1)
            # Before 2021, provider labels such as 新课标Ⅰ describe the
            # nationwide I/II/III family which older catalog titles call 全国Ⅰ.
            if prefix == "新课标" and year and int(year) <= 2020:
                return f"全国{number}卷"
            return f"{label}{number}卷"
    if "新课标" in compact and year and int(year) <= 2020:
        return "新课标卷（未分卷）"
    return ""


def identity(year: str, subject: str, displayed: str, fallback_region: str) -> tuple[str, str, str, str, str]:
    """Map a title to a conservative catalog-comparison identity.

    The last component retains 文/理.  It is intentionally not a content hash:
    rows with the same identity still require page/content review before any
    replacement decision.
    """
    family = paper_family(displayed, year)
    explicit = named_regions(displayed)
    if family.startswith(("全国", "新高考", "新课标", "大纲版")):
        region = "全国"
    elif explicit:
        region = "-".join(sorted(set(explicit), key=REGION_ORDER.__getitem__))
    else:
        region = fallback_region
    return year, region, subject, family or "地方卷", track(displayed)


def catalog_identity(row: dict[str, str]) -> tuple[str, str, str, str, str]:
    return identity(row["year"], row["subject"], f"{row.get('title', '')} {row.get('paper_type', '')}", row["region"])


def page_count(path: Path) -> tuple[int | None, str]:
    executable = shutil.which("pdfinfo")
    if not executable:
        return None, "pdfinfo unavailable"
    result = subprocess.run([executable, str(path)], capture_output=True, text=True, check=False)
    if result.returncode:
        return None, (result.stderr or result.stdout).strip().splitlines()[-1:][0] if (result.stderr or result.stdout).strip() else "pdfinfo failed"
    match = re.search(r"^Pages:\s*(\d+)\s*$", result.stdout, flags=re.MULTILINE)
    return (int(match.group(1)), "") if match else (None, "page count missing")


def inspect(path: Path, include_pages: bool) -> dict[str, str]:
    year = extract_year(path.stem)
    subject = subject_from_path(path)
    directory_scope = directory_region(path)
    year, region, subject, family, course = identity(year, subject, path.stem, directory_scope)
    pages, page_error = page_count(path) if include_pages else (None, "")
    explicit = named_regions(path.stem)
    warnings: list[str] = []
    if not year or not subject or not region:
        warnings.append("缺少年份、学科或使用范围")
    if explicit and family == "地方卷" and directory_scope and region != directory_scope:
        warnings.append("文件名省份与目录省份不一致")
    return {
        "source": str(path.relative_to(ROOT)), "year": year, "subject": subject,
        "directory_scope": directory_scope, "region": region, "paper_family": family,
        "track": course, "pages": "" if pages is None else str(pages),
        "page_error": page_error, "size_bytes": str(path.stat().st_size),
        "sha256": sha256(path), "warnings": "；".join(warnings),
    }


def audit(paths: list[Path], catalog_rows: list[dict[str, str]], include_pages: bool, workers: int) -> list[dict[str, str]]:
    existing_hashes = {row["sha256"].lower() for row in catalog_rows if row.get("sha256")}
    existing: dict[tuple[str, str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in catalog_rows:
        if row.get("status") != "withdrawn" and row.get("availability") == "local" and material_type(row) == "完整试卷":
            existing[catalog_identity(row)].append(row)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        entries = list(executor.map(lambda item: inspect(item, include_pages), paths))
    temp_counts = Counter((row["year"], row["region"], row["subject"], row["paper_family"], row["track"]) for row in entries)
    for row in entries:
        key = (row["year"], row["region"], row["subject"], row["paper_family"], row["track"])
        matches = existing.get(key, [])
        row["existing_record_ids"] = ";".join(item["record_id"] for item in matches)
        if row["warnings"]:
            row["action"] = "ambiguous_scope"
        elif row["sha256"].lower() in existing_hashes:
            row["action"] = "exact_existing_hash"
        elif matches:
            row["action"] = "same_identity_existing"
        elif temp_counts[key] > 1:
            row["action"] = "temp_identity_duplicate"
        else:
            row["action"] = "new_candidate"
        replaceable = [item for item in matches if item.get("source_type") == "local-upload" and item.get("license_status") == "unknown"]
        row["replacement_candidates"] = ";".join(item["record_id"] for item in replaceable)
    return entries


def render_summary(rows: list[dict[str, str]]) -> str:
    counts = Counter(row["action"] for row in rows)
    lines = [
        "# temp 版本 2 审计", "",
        "本页由 `python3 scripts/audit_temp_v2.py --with-pages` 生成。审计不会复制、移动或删除任何试卷。",
        "省份目录只代表资料提供者标注的使用范围；名称明确的全国、新课标或新高考卷统一按全国卷候选处理。`same_identity_existing` 只是候选映射，替换前仍须比较题干、页数和版面。", "",
        "## 总览", "", "| 结果 | 数量 |", "| --- | ---: |",
    ]
    for action in ("exact_existing_hash", "same_identity_existing", "temp_identity_duplicate", "new_candidate", "ambiguous_scope"):
        lines.append(f"| {action} | {counts[action]} |")
    lines += ["", "完整逐文件清单见 [temp-v2-audit.csv](temp-v2-audit.csv)，其中含原始相对路径、SHA-256、页数和候选替换记录。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--collection", default=DEFAULT_COLLECTION, help="temp/ 中待审计的目录名或前缀")
    parser.add_argument("--report", default="docs/temp-v2-audit.csv")
    parser.add_argument("--summary", default="docs/temp-v2-audit.md")
    parser.add_argument("--with-pages", action="store_true", help="use pdfinfo to collect page counts")
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    roots = [path for path in TEMP_ROOT.iterdir() if path.is_dir() and path.name.startswith(args.collection)]
    if not roots:
        parser.error(f"no temp collection starts with: {args.collection}")
    paths = sorted(path for root in roots for path in root.rglob("*.pdf"))
    rows = audit(paths, read_csv(CATALOG), args.with_pages, max(1, args.workers))
    fieldnames = list(rows[0]) if rows else ["source"]
    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    with report.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    summary = ROOT / args.summary
    summary.parent.mkdir(parents=True, exist_ok=True)
    summary.write_text(render_summary(rows), encoding="utf-8")
    print(" ".join(f"{action}={count}" for action, count in sorted(Counter(row['action'] for row in rows).items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
