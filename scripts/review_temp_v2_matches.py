#!/usr/bin/env python3
"""Compare audited temp-v2 identity matches with the current local catalog.

This is a review aid, not a migration command.  Equal extracted text and page
counts identify a small set that can be visually sampled before replacing an
unverified local-upload PDF.  Scanned or substantially different PDFs remain
explicitly pending rather than being guessed as duplicates.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import hashlib
import importlib.util
import logging
import re
from pathlib import Path

from stats import CATALOG, ROOT, read_csv

logging.getLogger("pypdf").setLevel(logging.ERROR)


def is_replacement_candidate(result: str, existing: dict[str, str]) -> bool:
    """Allow replacement only for a matching, explicitly unverified upload."""
    return (
        result == "full_text_and_page_match"
        and existing.get("status") != "verified"
        and existing.get("source_type") == "local-upload"
        and existing.get("license_status") == "unknown"
    )


def normalized_text(path: Path) -> tuple[int | None, str, str]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(path)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:  # A parser failure is a review result, not an import failure.
        return None, "", str(error).splitlines()[0]
    compact = re.sub(r"\s+", "", text)
    return len(reader.pages), compact, ""


def digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest() if text else ""


def similarity(first: str, second: str) -> float:
    """Return a layout-tolerant text similarity for human-review ordering."""
    # This is only a prioritisation signal, never proof that two papers are
    # identical.  Bounding the input and keeping SequenceMatcher's junk
    # heuristic makes a full 400-pair review tractable for long Chinese PDFs.
    return difflib.SequenceMatcher(None, first[:12_000], second[:12_000]).ratio()


def compare(audit_rows: list[dict[str, str]], catalog_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    catalog = {row["record_id"]: row for row in catalog_rows}
    text_cache: dict[Path, tuple[int | None, str, str]] = {}

    def read(path: Path) -> tuple[int | None, str, str]:
        if path not in text_cache:
            text_cache[path] = normalized_text(path)
        return text_cache[path]

    report: list[dict[str, str]] = []
    for candidate in audit_rows:
        if candidate["action"] != "same_identity_existing":
            continue
        candidate_path = ROOT / candidate["source"]
        candidate_pages, candidate_text, candidate_error = read(candidate_path)
        for record_id in filter(None, candidate["existing_record_ids"].split(";")):
            existing = catalog[record_id]
            existing_path = ROOT / existing["local_path"]
            existing_pages, existing_text, existing_error = read(existing_path)
            if candidate_error or existing_error or len(candidate_text) < 400 or len(existing_text) < 400:
                result = "text_unavailable_or_too_short"
            elif candidate_pages == existing_pages and digest(candidate_text) == digest(existing_text):
                result = "full_text_and_page_match"
            elif similarity(candidate_text, existing_text) >= 0.72:
                result = "likely_same_content_layout_difference"
            else:
                result = "content_or_page_difference"
            eligible = is_replacement_candidate(result, existing)
            report.append({
                "candidate_source": candidate["source"], "existing_record_id": record_id,
                "candidate_pages": "" if candidate_pages is None else str(candidate_pages),
                "existing_pages": "" if existing_pages is None else str(existing_pages),
                "candidate_text_sha256": digest(candidate_text), "existing_text_sha256": digest(existing_text),
                "candidate_text_chars": str(len(candidate_text)), "existing_text_chars": str(len(existing_text)),
                "text_similarity": f"{similarity(candidate_text, existing_text):.3f}" if candidate_text and existing_text else "",
                "result": result, "replacement_candidate": "yes" if eligible else "no",
                "candidate_error": candidate_error, "existing_error": existing_error,
            })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", default="docs/temp-v2-audit.csv")
    parser.add_argument("--report", default="docs/temp-v2-content-review.csv")
    parser.add_argument(
        "--remove-record-id",
        action="append",
        default=[],
        help=(
            "remove reviewed rows that have become exact-hash matches in the audit, "
            "without re-reading every candidate PDF"
        ),
    )
    args = parser.parse_args()
    output = ROOT / args.report
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.remove_record_id:
        with output.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fieldnames = list(reader.fieldnames or ["candidate_source"])
            removed = set(args.remove_record_id)
            rows = [row for row in reader if row.get("existing_record_id") not in removed]
    else:
        if importlib.util.find_spec("pypdf") is None:
            parser.error("pypdf is required for text comparison; install it or use the bundled workspace Python")
        with (ROOT / args.audit).open(newline="", encoding="utf-8") as handle:
            audit_rows = list(csv.DictReader(handle))
        rows = compare(audit_rows, read_csv(CATALOG))
        fieldnames = list(rows[0]) if rows else ["candidate_source"]
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fieldnames,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["result"]] = counts.get(row["result"], 0) + 1
    print(" ".join(f"{key}={value}" for key, value in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
