#!/usr/bin/env python3
"""Render a compact, conversation-independent status page for temp v2."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from apply_temp_v2_replacements import ADDITIONS, MATERIALIZATIONS, REPLACEMENTS
from stats import CATALOG, ROOT, material_type, read_csv


def read_optional(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def applied_counts(rows: list[dict[str, str]]) -> tuple[Counter[str], list[str]]:
    by_id = {row["record_id"]: row for row in rows}
    applied: Counter[str] = Counter()
    pending: list[str] = []
    registries = (
        ("replacement", REPLACEMENTS, "new_sha256"),
        ("addition", ADDITIONS, "sha256"),
        ("materialization", MATERIALIZATIONS, "sha256"),
    )
    for kind, registry, hash_field in registries:
        for record_id, decision in registry.items():
            row = by_id.get(record_id)
            if row and row.get("sha256") == decision[hash_field] and row.get("status") == "verified":
                applied[kind] += 1
            else:
                pending.append(record_id)
    return applied, sorted(pending)


def render() -> str:
    catalog = read_csv(CATALOG)
    audit = read_optional(ROOT / "docs" / "temp-v2-audit.csv")
    review = read_optional(ROOT / "docs" / "temp-v2-content-review.csv")
    sample = read_optional(ROOT / "docs" / "temp-v2-sample-review.csv")
    local_papers = [
        row for row in catalog
        if row.get("availability") == "local"
        and row.get("status") != "withdrawn"
        and material_type(row) == "完整试卷"
    ]
    unverified_uploads = [
        row for row in local_papers
        if row.get("status") != "verified"
        and row.get("source_type") == "local-upload"
        and row.get("license_status") == "unknown"
    ]
    actions = Counter(row.get("action", "") for row in audit)
    results = Counter(row.get("result", "") for row in review)
    applied, pending = applied_counts(catalog)
    lines = [
        "# temp 版本 2 处理状态", "",
        "这是与对话无关的短期工作记忆。后续处理先读本页与 `temp-v2-workflow.md`，不要把整份 PDF 或大型 CSV 装入对话上下文。", "",
        "## 当前快照", "",
        "| 指标 | 数量 |", "| --- | ---: |",
        f"| temp v2 PDF | {len(audit)} |",
        f"| 主库本地完整试卷 | {len(local_papers)} |",
        f"| 已验证本地完整试卷 | {sum(row.get('status') == 'verified' for row in local_papers)} |",
        f"| 仍未验证的本地上传主卷 | {len(unverified_uploads)} |",
        f"| 显式替换决策（已应用 / 登记） | {applied['replacement']} / {len(REPLACEMENTS)} |",
        f"| 显式新增决策（已应用 / 登记） | {applied['addition']} / {len(ADDITIONS)} |",
        f"| 外部候选落地（已应用 / 登记） | {applied['materialization']} / {len(MATERIALIZATIONS)} |",
        "", "## 审计队列", "",
        "| 结果 | 数量 |", "| --- | ---: |",
    ]
    for key in ("exact_existing_hash", "same_identity_existing", "temp_identity_duplicate", "new_candidate", "ambiguous_scope"):
        lines.append(f"| `{key}` | {actions[key]} |")
    lines += ["", "## 内容比对队列", "", "| 结果 | 数量 |", "| --- | ---: |"]
    for key in ("full_text_and_page_match", "likely_same_content_layout_difference", "content_or_page_difference", "text_unavailable_or_too_short"):
        lines.append(f"| `{key}` | {results[key]} |")
    eligible = sum(row.get("replacement_candidate") == "yes" for row in review)
    sample_results = Counter(row.get("review_result", "pending") or "pending" for row in sample)
    lines += [
        "", f"报告中仍标记为安全替换候选：**{eligible}**。", "",
        "## 分层抽验", "",
        f"共 **{len(sample)}** 份；待复核 **{sample_results['pending']}**，通过 **{sample_results['pass']}**，失败 **{sample_results['fail']}**。",
    ]
    if pending:
        lines += ["", "## 待应用的显式决策", "", *[f"- `{record_id}`" for record_id in pending]]
    else:
        lines += ["", "当前没有待应用的显式决策。"]
    lines += ["", "生成命令：`python3 scripts/temp_v2_status.py --write docs/temp-v2-status.md`", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", default="", help="write the status page instead of printing it")
    args = parser.parse_args()
    content = render()
    if args.write:
        destination = ROOT / args.write
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(content, encoding="utf-8")
    else:
        print(content, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
