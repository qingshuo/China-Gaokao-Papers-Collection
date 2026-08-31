# 贡献指南

感谢补充试卷来源。请先确认来源稳定、记录字段完整，并且不会把版权不明的文件直接提交进仓库。

## 数据格式

编辑 `data/exams.csv` 时保留现有列顺序。`record_id` 必须唯一，格式建议为 `年份-范围-科目-类型` 的短横线组合。`status` 使用 `planned`、`discovered`、`indexed`、`verified` 或 `withdrawn`；`availability` 使用 `none`、`external` 或 `local`。只有本地文件需要填写 `sha256`；不可托管的资料应提交具体外部链接和来源说明。

## 提交前检查

```bash
python3 scripts/stats.py --check
python3 scripts/stats.py --write docs/coverage.md
python3 scripts/stats.py --write-index docs/papers-index.md
python3 scripts/stats.py --write-year-index docs/year-index.md
python3 scripts/stats.py --write-region-index docs/region-index.md
python3 scripts/stats.py --write-subject-year-matrix docs/subject-year-matrix.md
python3 scripts/usage_scope_leads.py --check
python3 scripts/usage_scope_leads.py --write docs/usage-scope-leads.md
python3 scripts/audit_duplicates.py --write docs/candidate-duplicates.md
python3 scripts/audit_traceability.py --write docs/traceability.md
python3 -m unittest discover -s tests -v
```

Pull Request 请说明：来源 URL、试卷年份与范围、是否包含答案或解析、授权依据，以及是否验证过文件完整性。
