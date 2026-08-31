#!/usr/bin/env python3
"""Import individually reviewed Shanghai spring-exam mathematics papers.

The upstream archive may contain answer pages or non-exam practice materials.
Only a source file added to REVIEWED_PAPERS after first-page and page-boundary
inspection can be downloaded; answers are always stored outside the main-paper
directory.
"""

from __future__ import annotations

import argparse
import csv
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from pypdf import PdfReader, PdfWriter

from stats import CATALOG, ROOT, read_csv

REPOSITORY = "admin05/gaokaomath-archive"
RAW_ROOT = f"https://raw.githubusercontent.com/{REPOSITORY}/main/"
SOURCE_PREFIX = "春季高考"

# Each entry has been reviewed visually. answer_start is one-based.
REVIEWED_PAPERS = {
    "2017": {
        "filename": "2017春季上海.pdf",
        "answer_start": 4,
        "source_title": "2017年上海市春季高考数学试卷",
    },
    "2018": {
        "filename": "2018春季上海.pdf",
        "answer_start": 7,
        "source_title": "2018年上海市春季高考数学试卷",
    },
    "2019": {
        "filename": "2019春季上海.pdf",
        "answer_start": 4,
        "source_title": "2019年上海春季高考数学真题",
    },
    "2020": {
        "filename": "2020春季上海.pdf",
        "answer_start": 3,
        "source_title": "2020年上海市春季高考数学试卷",
    },
}


def fetch(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "China-Gaokao-Papers-Collection importer"})
    with urlopen(request, timeout=60) as response:
        return response.read()


def split_pdf(source: bytes, answer_start: int) -> tuple[bytes, bytes]:
    if not source.startswith(b"%PDF-"):
        raise ValueError("source is not a PDF")
    reader = PdfReader(BytesIO(source))
    if answer_start <= 1 or answer_start > len(reader.pages):
        raise ValueError(f"invalid answer page boundary {answer_start} for {len(reader.pages)} pages")

    def write_pages(pages: list[object]) -> bytes:
        writer = PdfWriter()
        for page in pages:
            writer.add_page(page)
        output = BytesIO()
        writer.write(output)
        result = output.getvalue()
        if not result.startswith(b"%PDF-"):
            raise ValueError("split output is not a PDF")
        return result

    return (
        write_pages(list(reader.pages[:answer_start - 1])),
        write_pages(list(reader.pages[answer_start - 1:])),
    )


def catalog_row(
    record_id: str,
    year: str,
    title: str,
    source_url: str,
    local_path: Path,
    content: bytes,
    material_type: str,
    notes: str,
) -> dict[str, str]:
    return {
        "record_id": record_id,
        "year": year,
        "region": "SH",
        "paper_type": "上海春考卷",
        "subject": "数学",
        "title": title,
        "source_url": source_url,
        "source_type": "github",
        "license_status": "permitted",
        "availability": "local",
        "status": "indexed",
        "local_path": str(local_path),
        "sha256": sha256(content).hexdigest(),
        "notes": notes,
        "material_type": material_type,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", choices=sorted(REVIEWED_PAPERS), required=True)
    parser.add_argument("--apply", action="store_true", help="download, split, and append catalog records")
    args = parser.parse_args()
    reviewed = REVIEWED_PAPERS[args.year]
    source_path = f"{SOURCE_PREFIX}/{args.year}/{reviewed['filename']}"
    source_url = RAW_ROOT + quote(source_path)
    print(f"year={args.year} source={source_url} mode={'apply' if args.apply else 'dry-run'}")
    if not args.apply:
        return 0

    source = fetch(source_url)
    reader = PdfReader(BytesIO(source))
    first_page = reader.pages[0].extract_text() or ""
    normalized_first_page = "".join(first_page.split())
    normalized_title = "".join(reviewed["source_title"].split())
    if normalized_title not in normalized_first_page or "练习" in normalized_first_page:
        raise ValueError("first-page identity check failed; refusing to import")
    questions, answers = split_pdf(source, reviewed["answer_start"])

    question_path = Path("papers") / args.year / "SH" / "数学" / f"{args.year}上海春季高考数学.pdf"
    answer_path = Path("papers/supplements") / args.year / "SH" / "数学" / f"{args.year}上海春季高考数学-参考答案.pdf"
    record_ids = {
        f"admin05-{args.year}-sh-spring-math",
        f"admin05-{args.year}-sh-spring-math-answer",
    }
    catalog_rows = read_csv(CATALOG)
    existing_ids = {row["record_id"] for row in catalog_rows}
    if existing_ids & record_ids:
        raise ValueError(f"catalog already contains: {', '.join(sorted(existing_ids & record_ids))}")
    destinations = [(ROOT / question_path, questions), (ROOT / answer_path, answers)]
    if any(path.exists() for path, _ in destinations):
        raise FileExistsError("refusing to overwrite an existing destination")

    notes = (
        f"来自 {REPOSITORY}；仓库声明 CC-BY-4.0；已逐页核验首页为“{reviewed['source_title']}”，"
        f"共 {len(reader.pages)} 页，前 {reviewed['answer_start'] - 1} 页为试题，后续答案已拆分到附属资料"
    )
    rows = [
        catalog_row(
            f"admin05-{args.year}-sh-spring-math", args.year, reviewed["source_title"],
            source_url, question_path, questions, "完整试卷", notes,
        ),
        catalog_row(
            f"admin05-{args.year}-sh-spring-math-answer", args.year, f"{reviewed['source_title']}参考答案",
            source_url, answer_path, answers, "附属资料", notes,
        ),
    ]
    written: list[Path] = []
    try:
        for path, content in destinations:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
            written.append(path)
        with CATALOG.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(catalog_rows[0]))
            writer.writeheader()
            writer.writerows(catalog_rows + rows)
    except Exception:
        for path in written:
            path.unlink(missing_ok=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
