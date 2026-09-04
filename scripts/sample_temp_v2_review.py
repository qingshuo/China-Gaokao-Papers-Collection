#!/usr/bin/env python3
"""Build a small deterministic, stratified visual-review sample."""

from __future__ import annotations

import argparse
import csv
import hashlib
import math
from collections import defaultdict
from pathlib import Path

from stats import ROOT

IDENTITY_FIELDS = ("year", "region", "subject", "paper_family", "track")
OUTPUT_FIELDS = (
    "sample_id", "action", "year", "subject", "region", "paper_family", "track",
    "pages", "source", "sha256", "existing_record_ids", "selection_reason", "review_result", "review_notes",
)
RISK_TERMS = ("答案", "解析", "回忆", "模拟", "预测", "知识点", "部分试题", "网盘", "公众号")


def rank(row: dict[str, str], seed: str) -> str:
    return hashlib.sha256(f"{seed}\0{row['source']}\0{row['sha256']}".encode()).hexdigest()


def unique_identities(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    """Choose one stable representative for repeated province-labelled identities."""
    representatives: dict[tuple[str, ...], dict[str, str]] = {}
    for row in rows:
        key = tuple(row.get(field, "") for field in IDENTITY_FIELDS)
        if key not in representatives or row["source"] < representatives[key]["source"]:
            representatives[key] = row
    return list(representatives.values())


def unique_hashes(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    representatives: dict[str, dict[str, str]] = {}
    for row in rows:
        key = row.get("sha256") or row["source"]
        if key not in representatives or row["source"] < representatives[key]["source"]:
            representatives[key] = row
    return list(representatives.values())


def high_risk(row: dict[str, str]) -> bool:
    return (
        row.get("action") == "ambiguous_scope"
        or bool(row.get("page_error"))
        or int(row.get("pages") or 0) <= 1
        or any(term in row.get("source", "") for term in RISK_TERMS)
    )


def sample_rows(rows: list[dict[str, str]], rate: float, minimum: int, seed: str) -> list[dict[str, str]]:
    selected = unique_hashes([row for row in rows if high_risk(row)])
    pool = unique_identities([
        row for row in rows
        if row.get("action") in {"same_identity_existing", "temp_identity_duplicate", "new_candidate"}
        and not high_risk(row)
    ])
    strata: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in pool:
        strata[(row["action"], row["subject"])].append(row)
    for stratum in strata.values():
        count = min(len(stratum), max(minimum, math.ceil(len(stratum) * rate)))
        selected.extend(sorted(stratum, key=lambda row: rank(row, seed))[:count])
    deduplicated = {row["source"]: row for row in selected}
    return sorted(deduplicated.values(), key=lambda row: (row["action"], row["subject"], row["year"], row["source"]))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit", default="docs/temp-v2-audit.csv")
    parser.add_argument("--report", default="docs/temp-v2-sample-review.csv")
    parser.add_argument("--rate", type=float, default=0.02)
    parser.add_argument("--minimum", type=int, default=1)
    parser.add_argument("--seed", default="temp-v2-v1")
    args = parser.parse_args()
    if not 0 < args.rate <= 1:
        parser.error("--rate must be greater than 0 and at most 1")
    with (ROOT / args.audit).open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    selected = sample_rows(rows, args.rate, max(1, args.minimum), args.seed)
    destination = ROOT / args.report
    destination.parent.mkdir(parents=True, exist_ok=True)
    previous: dict[str, dict[str, str]] = {}
    if destination.is_file():
        with destination.open(newline="", encoding="utf-8-sig") as handle:
            previous = {row["source"]: row for row in csv.DictReader(handle)}
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_FIELDS, lineterminator="\n")
        writer.writeheader()
        for number, row in enumerate(selected, 1):
            old = previous.get(row["source"], {})
            writer.writerow({
                **{field: row.get(field, "") for field in OUTPUT_FIELDS},
                "sample_id": f"sample-{number:03d}",
                "selection_reason": "high_risk_full_review" if high_risk(row) else "stratified_sample",
                "review_result": old.get("review_result", "pending"),
                "review_notes": old.get("review_notes", ""),
            })
    print(f"identities={len(unique_identities(rows))} sampled={len(selected)} rate={args.rate:.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
