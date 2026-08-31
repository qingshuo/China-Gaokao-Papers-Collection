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

# These files use a dense multi-column single-page layout.  They were rendered
# and visually reviewed as complete 1999 national papers; keep the exception
# explicit so a page-count heuristic cannot silently hide later defects.
REVIEWED_SINGLE_PAGE_MAIN_PAPERS = {
    "deekur-1987-math-f2d4e1b07aaa": "完整 1987 全国卷（文），单页密排版，已视觉复核",
    "deekur-1987-math-0b4d76e4d508": "完整 1987 全国卷（理），单页密排版，已视觉复核",
    "deekur-1988-math-65232ed91512": "完整 1988 全国卷（文），单页密排版，已视觉复核",
    "deekur-1988-math-0796587e94d6": "完整 1988 全国卷（理），单页密排版，已视觉复核",
    "deekur-1989-math-2fe91ea99a52": "完整 1989 全国卷（文），单页密排版，已视觉复核",
    "deekur-1989-math-e757068acbbc": "完整 1989 全国卷（理），单页密排版，已视觉复核",
    "deekur-1990-math-c74e7f34e64b": "完整 1990 上海卷，单页密排版，已视觉复核",
    "deekur-1990-math-b9d28672d531": "完整 1990 全国卷（文），单页密排版，已视觉复核",
    "deekur-1990-math-92bd3b182483": "完整 1990 全国卷（理），单页密排版，已视觉复核",
    "deekur-1991-math-9ebceeb1caf2": "完整 1991 三南共用卷，单页密排版，已视觉复核",
    "deekur-1991-math-dc5885349283": "完整 1991 全国卷（文），单页密排版，已视觉复核",
    "deekur-1991-math-9599225b2bf2": "完整 1991 全国卷（理），单页密排版，已视觉复核",
    "deekur-1992-math-edba4bab0493": "完整 1992 三南共用卷，单页密排版，已视觉复核",
    "deekur-1992-math-1cb0ae8e50ed": "完整 1992 全国卷（文），单页密排版，已视觉复核",
    "deekur-1992-math-9426374e5971": "完整 1992 全国卷（理），单页密排版，已视觉复核",
    "deekur-1993-math-3192f6df0209": "完整 1993 新高考共用卷（文），单页密排版，已视觉复核",
    "deekur-1993-math-0c645ba883c3": "完整 1993 新高考共用卷（理），单页密排版，已视觉复核",
    "deekur-1994-math-a943a6b50440": "完整 1994 全国新科目组卷（文），单页密排版，已视觉复核",
    "deekur-1994-math-8c793ca2efc9": "完整 1994 全国新科目组卷（理），单页密排版，已视觉复核",
    "deekur-1995-math-a4b5a4c82e74": "完整 1995 全国卷（文），单页密排版，已视觉复核",
    "deekur-1995-math-18d18ff50894": "完整 1995 全国卷（理），单页密排版，已视觉复核",
    "deekur-1996-math-ab4980abfb13": "完整 1996 全国卷（文），单页密排版，已视觉复核",
    "deekur-1996-math-99b971f953f3": "完整 1996 全国卷（理），单页密排版，已视觉复核",
    "deekur-1997-math-262d651dec63": "完整 1997 全国卷（文），单页密排版，已视觉复核",
    "deekur-1997-math-464ad1fc2bae": "完整 1997 全国卷（理），单页密排版，已视觉复核",
    "deekur-1998-math-b15ce2832513": "完整 1998 全国卷（文），单页密排版，已视觉复核",
    "deekur-1998-math-4acbfeaa77a2": "完整 1998 全国卷（理），单页密排版，已视觉复核",
    "deekur-1999-math-4938ecaede26": "完整 1999 全国卷（文），单页密排版，已视觉复核",
    "deekur-1999-math-b64634dd76f6": "完整 1999 全国卷（理），单页密排版，已视觉复核",
}


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


def audit(rows: list[dict[str, str]]) -> tuple[list[tuple[dict[str, str], str]], list[tuple[dict[str, str], int]], list[tuple[dict[str, str], int, str]], Counter[str]]:
    failures: list[tuple[dict[str, str], str]] = []
    short_main_papers: list[tuple[dict[str, str], int]] = []
    reviewed_single_page_papers: list[tuple[dict[str, str], int, str]] = []
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
            review_note = REVIEWED_SINGLE_PAGE_MAIN_PAPERS.get(row["record_id"])
            if review_note:
                reviewed_single_page_papers.append((row, pages, review_note))
            else:
                short_main_papers.append((row, pages))
    return failures, short_main_papers, reviewed_single_page_papers, counts


def render_markdown(
    failures: list[tuple[dict[str, str], str]], short_main_papers: list[tuple[dict[str, str], int]],
    reviewed_single_page_papers: list[tuple[dict[str, str], int, str]], counts: Counter[str]
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
    if reviewed_single_page_papers:
        lines += ["", "## 已复核的单页完整卷", "", "以下文件为密排单页版，已视觉确认包含完整题目；保留在此以便后续复核。", "", "| 记录 ID | 年份 | 页数 | 试卷 | 复核结论 |", "| --- | ---: | ---: | --- | --- |"]
        for row, pages, note in reviewed_single_page_papers:
            title = row["title"].replace("|", "\\|")
            link = "../" + quote(row["local_path"], safe="/")
            lines.append(f"| `{row['record_id']}` | {row['year']} | {pages} | [{title}]({link}) | {note} |")
    if not failures and not short_main_papers:
        lines += ["", "> 当前所有本地 PDF 均可解析，且完整试卷中没有页数不超过 1 页的候选。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the PDF-integrity report")
    args = parser.parse_args()
    failures, short_main_papers, reviewed_single_page_papers, counts = audit(read_csv(CATALOG))
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(failures, short_main_papers, reviewed_single_page_papers, counts), encoding="utf-8")
    print(f"pdfs_parsed={sum(counts.values())} failures={len(failures)} short_main_papers={len(short_main_papers)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
