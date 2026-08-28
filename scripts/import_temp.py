#!/usr/bin/env python3
"""Import exam documents from temp/ with content deduplication."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import quote, unquote

ROOT = Path(__file__).resolve().parents[1]
TEMP = ROOT / "temp"
CATALOG = ROOT / "data" / "exams.csv"
SUPPORTED = {".pdf", ".docx", ".doc", ".tex"}
# These terms identify promotional material or preparation exercises rather
# than an examination paper.  Check the complete relative path because some
# collections put unrelated files in a directory named "网盘群".
NOISE = (
    "公众号", "网盘", "进群", "加群", "二维码", "提分必备", "广告",
    "一轮复习", "二轮复习", "考点帮", "压轴题一览", "模拟题", "预测题",
    "知识点", "专项练习", "专题练习", "作业题",
)
DOCX_NOISE = ("公众号", "微信", "网盘", "加群", "二维码", "关注我们", "扫码", "QQ群", "大才酷")
SUBJECTS = ("语文", "数学", "英语", "日语", "物理", "化学", "生物", "地理", "历史", "政治")
REGIONS = (
    ("内蒙古", "NM"), ("黑龙江", "HL"), ("宁夏", "NX"), ("新疆", "XJ"),
    ("北京", "BJ"), ("天津", "TJ"), ("河北", "HE"), ("山西", "SX"),
    ("辽宁", "LN"), ("吉林", "JL"), ("上海", "SH"), ("江苏", "JS"),
    ("浙江", "ZJ"), ("安徽", "AH"), ("福建", "FJ"), ("江西", "JX"),
    ("山东", "SD"), ("河南", "HA"), ("湖北", "HB"), ("湖南", "HN"),
    ("广东", "GD"), ("广西", "GX"), ("海南", "HI"), ("重庆", "CQ"),
    ("四川", "SC"), ("贵州", "GZ"), ("云南", "YN"), ("西藏", "XZ"),
    ("陕西", "SN"), ("甘肃", "GS"), ("青海", "QH"),
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def extract_year(text: str) -> str | None:
    years = re.findall(r"(?:19|20)\d{2}", text)
    return years[-1] if years else None


def classify(path: Path) -> tuple[str | None, str, str, str]:
    text = str(path)
    name = path.stem
    year = extract_year(text)
    # The filename is generally specific (for example, "广东物理.pdf"),
    # while parent directories often contain a list of every subject.
    subject = ""
    for candidate in ("生命科学",) + SUBJECTS:
        if candidate in name:
            subject = "生物" if candidate == "生命科学" else candidate
            break
    if not subject:
        for candidate in ("生命科学",) + SUBJECTS:
            if candidate in text:
                subject = "生物" if candidate == "生命科学" else candidate
                break
    if not subject and "理综" in text:
        subject = "综合理综"
    if not subject and "文综" in text:
        subject = "综合文综"
    # A single explicit province wins over generic labels such as "新高考".
    # If a file names several provinces, retain it as a multi-province paper
    # under 全国; the title still records the original scope.
    region_codes = [code for label, code in REGIONS if label in text]
    unique_regions = list(dict.fromkeys(region_codes))
    region = unique_regions[0] if len(unique_regions) == 1 else "全国"
    if "答案" in name and "解析" in name:
        variant = "试题答案解析"
    elif "解析" in name:
        variant = "解析版"
    elif "答案" in name:
        variant = "答案"
    elif "听力" in name:
        variant = "听力"
    else:
        variant = "原卷"
    return year, region, subject, variant


def docx_contains_noise(path: Path) -> bool:
    """Check document XML, including headers, for embedded promotion text."""
    try:
        with zipfile.ZipFile(path) as archive:
            content = "\n".join(
                archive.read(name).decode("utf-8", errors="ignore")
                for name in archive.namelist()
                if name.endswith(".xml")
            )
    except zipfile.BadZipFile:
        return False
    return any(token in content for token in DOCX_NOISE)


def is_candidate(path: Path, years: set[str]) -> bool:
    if path.suffix.lower() not in SUPPORTED or path.name == ".DS_Store":
        return False
    if any(token in str(path) for token in NOISE):
        return False
    if path.suffix.lower() == ".docx" and docx_contains_noise(path):
        return False
    year, _, subject, _ = classify(path)
    if year not in years or not subject:
        return False
    return any(token in str(path) for token in ("高考", "真题", "试卷", "普通高中学业水平选择性考试"))


def existing_hashes() -> set[str]:
    hashes: set[str] = set()
    with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            path = ROOT / row.get("local_path", "")
            if path.is_file():
                hashes.add(sha256(path))
            if row.get("sha256"):
                hashes.add(row["sha256"].lower())
    return hashes


def unique_destination(base: Path, filename: str, digest: str) -> Path:
    destination = base / filename
    if not destination.exists():
        return destination
    return base / f"{destination.stem}--{digest[:8]}{destination.suffix}"


def convert_doc(source: Path, output_dir: Path) -> Path | None:
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            ["soffice", "--headless", "--convert-to", "pdf", "--outdir", str(output_dir), str(source)],
            capture_output=True,
            text=True,
            check=False,
            timeout=45,
        )
    except subprocess.TimeoutExpired:
        return None
    converted = output_dir / f"{source.stem}.pdf"
    if result.returncode != 0 or not converted.is_file():
        return None
    return converted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--years", default="2022-2026", help="year range, for example 2022-2026")
    parser.add_argument("--copy", action="store_true", help="copy files and append catalog rows")
    parser.add_argument("--report", default="docs/temp-import-report.csv")
    parser.add_argument("--convert-doc", action="store_true", help="convert legacy .doc files to PDF")
    parser.add_argument(
        "--extensions", default=",".join(sorted(SUPPORTED)),
        help="comma-separated extensions to import, for example .pdf,.docx",
    )
    parser.add_argument(
        "--repair-local-paths", action="store_true",
        help="move earlier imports from ignored papers/temp/ to the standard papers/ layout",
    )
    parser.add_argument(
        "--restore-legacy-docs", metavar="REPORT",
        help="restore original DOC files when PDF conversion fails visual QA",
    )
    parser.add_argument(
        "--purge-content-noise", action="store_true",
        help="remove earlier temp imports whose DOCX XML contains promotion text",
    )
    parser.add_argument("--trash-dir", help="explicit directory used with --purge-content-noise")
    parser.add_argument(
        "--normalize-local-filenames", action="store_true",
        help="remove importer hash suffixes when the original name is available",
    )
    args = parser.parse_args()
    start, end = (int(part) for part in args.years.split("-", 1))
    years = {str(year) for year in range(start, end + 1)}
    if args.repair_local_paths:
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            fieldnames = list(csv.DictReader(handle).fieldnames or [])
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        moved = 0
        for row in rows:
            current = Path(row.get("local_path", ""))
            parts = current.parts
            if len(parts) < 6 or parts[:2] != ("papers", "temp"):
                continue
            _, _, year, subject, region, filename = parts
            source = ROOT / current
            destination = unique_destination(ROOT / "papers" / year / region / subject, filename, row["sha256"])
            if source.is_file():
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(source, destination)
                row["local_path"] = str(destination.relative_to(ROOT))
                moved += 1
        with CATALOG.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"moved={moved}")
        return 0

    if args.restore_legacy_docs:
        with Path(args.restore_legacy_docs).open(newline="", encoding="utf-8-sig") as handle:
            legacy_sources = {
                row["source"] for row in csv.DictReader(handle)
                if Path(row["source"]).suffix.lower() == ".doc" and row["action"] == "candidate"
            }
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            fieldnames = list(csv.DictReader(handle).fieldnames or [])
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        restored = 0
        for row in rows:
            source_url = row.get("source_url", "")
            if not source_url.startswith("local://temp/"):
                continue
            source = TEMP / unquote(source_url.removeprefix("local://temp/"))
            if str(source.relative_to(ROOT)) not in legacy_sources:
                continue
            old_destination = ROOT / row["local_path"]
            destination = old_destination.with_suffix(".doc")
            if not source.is_file():
                continue
            shutil.copy2(source, destination)
            if old_destination.is_file():
                old_destination.unlink()
            row["local_path"] = str(destination.relative_to(ROOT))
            row["sha256"] = sha256(destination)
            row["notes"] = re.sub(r"格式：pdf$", "格式：doc（PDF 转换因字体缺失未采用）", row["notes"])
            restored += 1
        with CATALOG.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"restored={restored}")
        return 0

    if args.purge_content_noise:
        if not args.trash_dir:
            parser.error("--purge-content-noise requires --trash-dir")
        trash_dir = Path(args.trash_dir)
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            fieldnames = list(csv.DictReader(handle).fieldnames or [])
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        kept: list[dict[str, str]] = []
        withdrawn = 0
        for row in rows:
            local = ROOT / row.get("local_path", "")
            is_temp_docx = row.get("record_id", "").startswith("temp-") and local.suffix.lower() == ".docx"
            if is_temp_docx and row.get("year") in years and local.is_file() and docx_contains_noise(local):
                destination = trash_dir / local.relative_to(ROOT)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(local, destination)
                withdrawn += 1
                continue
            kept.append(row)
        with CATALOG.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(kept)
        print(f"withdrawn={withdrawn}")
        return 0

    if args.normalize_local_filenames:
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            fieldnames = list(csv.DictReader(handle).fieldnames or [])
        with CATALOG.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        normalized = 0
        for row in rows:
            local = ROOT / row.get("local_path", "")
            suffix = f"--{row.get('sha256', '')[:8]}"
            if not suffix or not local.is_file() or not local.stem.endswith(suffix):
                continue
            destination = local.with_name(f"{local.stem[:-len(suffix)]}{local.suffix}")
            if destination.exists():
                continue
            shutil.move(local, destination)
            row["local_path"] = str(destination.relative_to(ROOT))
            normalized += 1
        with CATALOG.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        print(f"normalized={normalized}")
        return 0

    extensions = {suffix.strip().lower() for suffix in args.extensions.split(",") if suffix.strip()}
    unsupported = extensions - SUPPORTED
    if unsupported:
        parser.error(f"unsupported extensions: {', '.join(sorted(unsupported))}")
    candidates = sorted(
        path for path in TEMP.rglob("*")
        if path.is_file() and path.suffix.lower() in extensions and is_candidate(path, years)
    )
    seen = existing_hashes()
    report_rows: list[dict[str, str]] = []
    catalog_rows: list[list[str]] = []
    temp_conversion = Path(tempfile.mkdtemp(prefix="gaokao-import-"))
    try:
        for source in candidates:
            year, region, subject, variant = classify(source)
            source_for_copy = source
            imported_ext = source.suffix.lower()
            if args.copy and args.convert_doc and imported_ext == ".doc":
                converted = convert_doc(source, temp_conversion)
                if not converted:
                    report_rows.append({
                        "source": str(source.relative_to(ROOT)), "year": year or "", "region": region,
                        "subject": subject, "variant": variant, "source_sha256": sha256(source),
                        "stored_sha256": "", "action": "conversion-failed", "local_path": "",
                    })
                    continue
                source_for_copy = converted
                imported_ext = ".pdf"
            digest = sha256(source_for_copy)
            action = "duplicate" if digest in seen else "candidate"
            destination = ""
            if args.copy and action == "candidate":
                safe_name = source_for_copy.name
                destination_path = unique_destination(
                    ROOT / "papers" / year / region / subject,
                    safe_name,
                    digest,
                )
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_for_copy, destination_path)
                destination = str(destination_path.relative_to(ROOT))
                seen.add(digest)
                catalog_rows.append([
                    f"temp-{year}-{subject}-{digest[:12]}", year, region, variant, subject,
                    source_for_copy.stem, f"local://temp/{quote(str(source.relative_to(TEMP)), safe='/')}",
                    "local-upload", "unknown", "local", "indexed", destination, digest,
                    f"用户 temp 目录导入；原始相对路径：{source.relative_to(TEMP)}；格式：{imported_ext.lstrip('.')}",
                ])
            report_rows.append({
                "source": str(source.relative_to(ROOT)), "year": year or "", "region": region,
                "subject": subject, "variant": variant, "source_sha256": sha256(source),
                "stored_sha256": digest, "action": action, "local_path": destination,
            })
    finally:
        shutil.rmtree(temp_conversion, ignore_errors=True)

    report_path = ROOT / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(report_rows[0]) if report_rows else ["source"])
        writer.writeheader()
        writer.writerows(report_rows)
    if args.copy and catalog_rows:
        with CATALOG.open("a", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(catalog_rows)
    print(f"candidates={len(candidates)} imported={sum(row['action'] == 'candidate' for row in report_rows)} duplicates={sum(row['action'] == 'duplicate' for row in report_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
