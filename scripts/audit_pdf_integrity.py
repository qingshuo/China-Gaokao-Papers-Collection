#!/usr/bin/env python3
"""Check cataloged PDFs can be parsed and surface unusually short main papers."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, ROOT, material_type, read_csv


def pages_from_pdfinfo(output: str) -> int | None:
    match = re.search(r"^Pages:\s*(\d+)\s*$", output, flags=re.MULTILINE)
    return int(match.group(1)) if match else None


def inspect_pdf(path: Path, executable: str | None = None) -> tuple[int | None, str | None]:
    """Return `(page_count, error)` using Poppler without modifying the file."""
    command = executable or shutil.which("pdfinfo")
    if not command:
        return None, "pdfinfo is unavailable"
    result = subprocess.run([command, str(path)], capture_output=True, text=True, check=False)
    if result.returncode:
        message = (result.stderr or result.stdout).strip().splitlines()
        return None, message[-1] if message else f"pdfinfo exited with {result.returncode}"
    pages = pages_from_pdfinfo(result.stdout)
    return (pages, None) if pages is not None else (None, "pdfinfo did not report a page count")


def audit(rows: list[dict[str, str]]) -> tuple[list[tuple[dict[str, str], str]], list[tuple[dict[str, str], int]], Counter[str]]:
    failures: list[tuple[dict[str, str], str]] = []
    short_main_papers: list[tuple[dict[str, str], int]] = []
    counts: Counter[str] = Counter()
    for row in rows:
        if row.get("status") == "withdrawn" or row.get("availability") != "local":
            continue
        if Path(row["local_path"]).suffix.lower() != ".pdf":
            continue
        pages, error = inspect_pdf(ROOT / row["local_path"])
        if error:
            failures.append((row, error))
            continue
        counts[material_type(row)] += 1
        if material_type(row) == "完整试卷" and pages is not None and pages <= 1:
            short_main_papers.append((row, pages))
    return failures, short_main_papers, counts


def render_markdown(
    failures: list[tuple[dict[str, str], str]], short_main_papers: list[tuple[dict[str, str], int]], counts: Counter[str]
) -> str:
    total = sum(counts.values()) + len(failures)
    lines = [
        "# PDF 完整性审计", "",
        "本页由 `python3 scripts/audit_pdf_integrity.py --write docs/pdf-integrity.md` 自动生成。",
        "脚本调用 Poppler `pdfinfo` 只读解析 PDF，以确认文件可打开并取得页数；它不验证题目是否真实、卷种是否正确或是否获得再发布许可。", "",
        "## 总览", "",
        f"- 已检查 PDF：**{total}**",
        f"- 可解析：**{sum(counts.values())}**",
        f"- 解析失败：**{len(failures)}**",
        f"- 页数不超过 1 页的完整试卷候选：**{len(short_main_papers)}**", "",
        "## 按资料类别的可解析 PDF", "", "| 资料类别 | 数量 |", "| --- | ---: |",
    ]
    for category in ("完整试卷", "附属资料", "片段资料"):
        lines.append(f"| {category} | {counts[category]} |")
    if failures:
        lines += ["", "## 解析失败", "", "| 记录 ID | 试卷 | 错误 |", "| --- | --- | --- |"]
        for row, error in failures:
            title = row["title"].replace("|", "\\|")
            link = "../" + quote(row["local_path"], safe="/")
            lines.append(f"| `{row['record_id']}` | [{title}]({link}) | {error.replace('|', '\\|')} |")
    if short_main_papers:
        lines += ["", "## 页数异常候选", "", "单页完整卷未必错误，但应复核是否仅导入了封面、单页试题或下载失败版本。", "", "| 记录 ID | 年份 | 地区 | 科目 | 页数 | 试卷 |", "| --- | ---: | --- | --- | ---: | --- |"]
        for row, pages in short_main_papers:
            title = row["title"].replace("|", "\\|")
            link = "../" + quote(row["local_path"], safe="/")
            lines.append(f"| `{row['record_id']}` | {row['year']} | {row['region']} | {row['subject']} | {pages} | [{title}]({link}) |")
    if not failures and not short_main_papers:
        lines += ["", "> 当前所有本地 PDF 均可解析，且完整试卷中没有页数不超过 1 页的候选。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the PDF-integrity report")
    args = parser.parse_args()
    failures, short_main_papers, counts = audit(read_csv(CATALOG))
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(failures, short_main_papers, counts), encoding="utf-8")
    print(f"pdfs_parsed={sum(counts.values())} failures={len(failures)} short_main_papers={len(short_main_papers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
