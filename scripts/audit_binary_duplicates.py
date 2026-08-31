#!/usr/bin/env python3
"""Report exact byte-identical catalog files without deleting any record."""

from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote

from stats import CATALOG, ROOT, material_type, read_csv


def exact_hash_groups(rows: list[dict[str, str]]) -> list[tuple[str, list[dict[str, str]]]]:
    """Return active local-record groups sharing an identical SHA-256 digest."""
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        if row.get("status") == "withdrawn" or row.get("availability") != "local":
            continue
        digest = row.get("sha256", "").lower()
        if digest:
            groups[digest].append(row)
    return sorted((digest, group) for digest, group in groups.items() if len(group) > 1)


def render_markdown(groups: list[tuple[str, list[dict[str, str]]]]) -> str:
    lines = [
        "# 完全相同文件审计", "",
        "本页由 `python3 scripts/audit_binary_duplicates.py --write docs/binary-duplicates.md` 自动生成。",
        "分组依据是 SHA-256 完全一致，说明文件字节相同；它仍**不自动删除**记录，因为不同地区、卷种或资料类别可能错误地共用了同一文件，需要人工确认目录身份。", "",
        f"当前共有 **{len(groups)} 组**完全相同文件，涉及 **{sum(len(group) for _, group in groups)} 条**目录记录。", "",
    ]
    for digest, group in groups:
        lines += [f"## `{digest}`", "", "| 记录 ID | 年份 | 地区 | 科目 | 资料类别 | 试卷 | 文件 |", "| --- | ---: | --- | --- | --- | --- | --- |"]
        for row in sorted(group, key=lambda item: (item["year"], item["region"], item["subject"], item["record_id"])):
            file_link = "../" + quote(row["local_path"], safe="/")
            title = row["title"].replace("|", "\\|")
            lines.append(
                f"| `{row['record_id']}` | {row['year']} | {row['region']} | {row['subject']} | {material_type(row)} | "
                f"{title} | [{Path(row['local_path']).name}]({file_link}) |"
            )
        lines.append("")
    lines += ["> 发现分组后，先比对卷种、适用范围与页面内容；确认是同一资料的冗余副本后，再优先保留 PDF 或来源/许可更清晰的版本。", ""]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", metavar="PATH", help="write the binary-duplicate report")
    args = parser.parse_args()
    groups = exact_hash_groups(read_csv(CATALOG))
    if args.write:
        output = Path(args.write)
        if not output.is_absolute():
            output = ROOT / output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(render_markdown(groups), encoding="utf-8")
    print(f"exact_hash_groups={len(groups)} records={sum(len(group) for _, group in groups)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
