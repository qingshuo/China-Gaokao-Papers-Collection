#!/usr/bin/env python3
"""Check cataloged DOCX files are readable Office containers with a main document."""

from __future__ import annotations

import argparse
import zipfile
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, ROOT, material_type, read_csv

MAIN_DOCUMENT = "word/document.xml"
CONTENT_TYPES = "[Content_Types].xml"


def inspect_docx(path: Path) -> str | None:
    """Return a structural error or None; the document is never modified."""
    try:
        with zipfile.ZipFile(path) as archive:
            bad_member = archive.testzip()
            if bad_member:
                return f"corrupt ZIP member: {bad_member}"
            names = set(archive.namelist())
    except zipfile.BadZipFile:
        return "not a readable Office ZIP container"
    if CONTENT_TYPES not in names:
        return "Office content-types manifest is missing"
    if MAIN_DOCUMENT not in names:
        return "Word main document XML is missing"
    return None


def audit(rows: list[dict[str, str]]) -> tuple[list[tuple[dict[str, str], str]], Counter[str]]:
    failures: list[tuple[dict[str, str], str]] = []
    counts: Counter[str] = Counter()
    for row in rows:
        if row.get("status") == "withdrawn" or row.get("availability") != "local":
            continue
        if Path(row["local_path"]).suffix.lower() != ".docx":
            continue
        error = inspect_docx(ROOT / row["local_path"])
        if error:
            failures.append((row, error))
        else:
            counts[material_type(row)] += 1
    return failures, counts


def render_markdown(failures: list[tuple[dict[str, str], str]], counts: Counter[str]) -> str:
    total = sum(counts.values()) + len(failures)
    lines = [
        "# DOCX 完整性审计", "",
        "本页由 `python3 scripts/audit_docx_integrity.py --write docs/docx-integrity.md` 自动生成。",
        "脚本只读检查 DOCX 的 Office ZIP 容器、内容清单和 Word 主文档 XML；它不验证版式、题目真实性、卷种或再发布许可。", "",
        "## 总览", "",
        f"- 已检查 DOCX：**{total}**",
        f"- 结构完整：**{sum(counts.values())}**",
        f"- 结构异常：**{len(failures)}**", "",
        "## 按资料类别的结构完整 DOCX", "", "| 资料类别 | 数量 |", "| --- | ---: |",
    ]
    for category in ("完整试卷", "附属资料", "片段资料"):
        lines.append(f"| {category} | {counts[category]} |")
    if failures:
        lines += ["", "## 结构异常", "", "| 记录 ID | 试卷 | 错误 |", "| --- | --- | --- |"]
        for row, error in failures:
            title = row["title"].replace("|", "\\|")
            link = "../" + quote(row["local_path"], safe="/")
            escaped_error = error.replace("|", "\\|")
            lines.append(f"| `{row['record_id']}` | [{title}]({link}) | {escaped_error} |")
    else:
        lines += ["", "> 当前所有本地 DOCX 均可作为完整 Office 文档容器读取，并包含 Word 主文档 XML。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the DOCX-integrity report")
    args = parser.parse_args()
    failures, counts = audit(read_csv(CATALOG))
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(failures, counts), encoding="utf-8")
    print(f"docx_valid={sum(counts.values())} failures={len(failures)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
