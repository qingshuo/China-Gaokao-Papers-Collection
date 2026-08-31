#!/usr/bin/env python3
"""Import an explicitly selected historical mathematics batch from deekur/gaokaomath."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import quote, unquote
from urllib.request import Request, urlopen

from stats import CATALOG, REGIONS, ROOT, read_csv

REPOSITORY = "deekur/gaokaomath"
BRANCH = "main"
TREE_URL = f"https://api.github.com/repos/{REPOSITORY}/git/trees/{BRANCH}?recursive=1"
RAW_ROOT = f"https://raw.githubusercontent.com/{REPOSITORY}/{BRANCH}/"

# These two files are stored under the upstream 2007 directory, but their
# filenames mistakenly begin with "2002".  Their rendered first pages say
# "2007 普通高等学校招生考试（大纲卷 II）".  Keep the raw URL untouched while
# correcting only the catalog title and making the discrepancy explicit.
KNOWN_TITLE_YEAR_MISMATCHES = {
    "普通高考/2007/2002大纲2文(黑龙江,吉林,贵州,新疆,内蒙古,青海,云南,西藏,甘肃).pdf",
    "普通高考/2007/2002大纲2理(黑龙江,吉林,贵州,新疆,内蒙古,青海,云南,西藏,甘肃).pdf",
}

# These scans are described only as an "old-subject group".  The rendered
# pages identify the subject but not the province(s) or national usage range,
# so they must not be silently classified as nationwide papers.  Keep the
# upstream paths as research leads until an authoritative scope is found.
UNRESOLVED_SCOPE_PATHS = {
    "普通高考/1994/1994旧科目组文.pdf",
    "普通高考/1994/1994旧科目组理.pdf",
}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "China-Gaokao-Papers-Collection importer"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def source_paths(year: str) -> list[str]:
    tree = json.loads(fetch(TREE_URL))
    if tree.get("truncated"):
        raise ValueError("GitHub tree response is truncated; refuse to import an incomplete batch")
    prefix = f"普通高考/{year}/"
    return sorted(item["path"] for item in tree["tree"] if item["type"] == "blob" and item["path"].startswith(prefix) and item["path"].endswith(".pdf"))


def eligible_source_paths(paths: list[str]) -> tuple[list[str], list[str]]:
    """Separate files with an evidenced geographic scope from research leads."""
    eligible = [path for path in paths if path not in UNRESOLVED_SCOPE_PATHS]
    skipped = [path for path in paths if path in UNRESOLVED_SCOPE_PATHS]
    return eligible, skipped


def region_for_filename(filename: str, region_rows: list[dict[str, str]]) -> str:
    if any(token in filename for token in ("全国", "新课标", "大纲", "延考")):
        return "全国"
    matches = [row for row in region_rows if row["name"] in filename]
    if len(matches) > 1:
        return "-".join(sorted(row["code"] for row in matches))
    if len(matches) != 1:
        raise ValueError(f"cannot determine one region from filename: {filename}")
    return matches[0]["code"]


def record_id(year: str, filename: str) -> str:
    digest = hashlib.sha256(filename.encode("utf-8")).hexdigest()[:12]
    return f"deekur-{year}-math-{digest}"


def title_for_path(year: str, path: str) -> tuple[str, str]:
    """Return an audited display title without silently accepting a wrong year."""
    title = Path(path).stem
    match = re.match(r"(\d{4})", title)
    if not match or match.group(1) == year:
        return title, ""
    if path not in KNOWN_TITLE_YEAR_MISMATCHES:
        raise ValueError(
            f"source filename year {match.group(1)} disagrees with requested directory year {year}: {path}"
        )
    return (
        f"{year}{title[4:]}",
        f"上游路径文件名以 {match.group(1)} 开头，但首页标题已人工核验为 {year} 年；目录标题已按首页更正，原始 URL 保留不变",
    )


def build_rows(year: str, paths: list[str], region_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in paths:
        filename = Path(path).name
        region = region_for_filename(filename, region_rows)
        title, title_note = title_for_path(year, path)
        notes = "来自 deekur/gaokaomath；仓库声明 CC-BY-4.0；历史回溯批次，保留原文件名和原始 URL；具体卷种范围仍待逐页及官方来源核验"
        if title_note:
            notes = f"{notes}；{title_note}"
        if "-" in region:
            names_by_code = {row["code"]: row["name"] for row in region_rows}
            scope = "、".join(names_by_code[code] for code in region.split("-"))
            notes = f"{notes}；文件名覆盖 {scope}，作为跨省共用卷单独归类并只存一份文件"
        rows.append({
            "record_id": record_id(year, filename),
            "year": year,
            "region": region,
            "paper_type": "普通高考",
            "subject": "数学",
            "title": title,
            "source_url": RAW_ROOT + quote(path),
            "source_type": "github",
            "license_status": "permitted",
            "availability": "local",
            "status": "indexed",
            "local_path": "",
            "sha256": "",
            "notes": notes,
            "material_type": "完整试卷",
        })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, help="year directory to import, e.g. 2016")
    parser.add_argument("--apply", action="store_true", help="download files and append catalog rows")
    args = parser.parse_args()
    year = args.year
    paths, skipped = eligible_source_paths(source_paths(year))
    regions = read_csv(REGIONS)
    rows = build_rows(year, paths, regions)
    print(f"year={year} candidates={len(rows)} mode={'apply' if args.apply else 'dry-run'}")
    for path in skipped:
        print(f"skipped-unresolved-scope {path}")
    for row in rows:
        print(f"{row['record_id']} {row['region']} {row['title']}")
    if not args.apply:
        return 0

    catalog_rows = read_csv(CATALOG)
    existing_ids = {row["record_id"] for row in catalog_rows}
    duplicates = existing_ids & {row["record_id"] for row in rows}
    if duplicates:
        raise ValueError(f"catalog already contains import IDs: {', '.join(sorted(duplicates))}")
    downloads: list[tuple[dict[str, str], Path, bytes]] = []
    for row in rows:
        source_path = unquote(row["source_url"].removeprefix(RAW_ROOT))
        destination = ROOT / "papers" / year / row["region"] / "数学" / Path(source_path).name
        if destination.exists():
            raise FileExistsError(f"refusing to overwrite existing file: {destination.relative_to(ROOT)}")
        content = fetch(row["source_url"])
        if not content.startswith(b"%PDF-"):
            raise ValueError(f"download is not a PDF: {row['source_url']}")
        downloads.append((row, destination, content))
    written: list[Path] = []
    try:
        for row, destination, content in downloads:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            written.append(destination)
            row["local_path"] = str(destination.relative_to(ROOT))
            row["sha256"] = hashlib.sha256(content).hexdigest()
    except Exception:
        for destination in written:
            destination.unlink(missing_ok=True)
        raise
    fieldnames = list(catalog_rows[0])
    with CATALOG.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(catalog_rows + rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
