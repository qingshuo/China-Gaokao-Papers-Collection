# temp 版本 2 整理流程

本流程处理 `temp/版本2：*（2008-2024）` 省份分类资料。`temp/` 是只读候选区，`data/exams.csv` 是唯一事实源，`papers/` 只放已经显式决策落库的文件。

## 快速验证原则

- **全量自动门禁**：对全部候选检查文件签名、SHA-256、PDF 可解析性、页数、年份/学科/卷别映射与文件名风险词。任何自动门禁失败的文件不进入抽验通过批次。
- **先合并后检查**：二进制哈希相同只验一次；同一年份、范围、学科、卷别和文/理身份在多个省份目录重复时，抽一个代表，不按路径数量重复看卷。
- **确定性分层抽验**：按“审计结果 × 学科”分层，默认每层抽 2%、至少 1 份；`ambiguous_scope`、单页、损坏、文本过短或风险词命中的文件全检。抽样由固定 seed 生成，可重复。
- **失败即扩检**：任一抽样出现错卷、残卷、答案/解析混入或身份冲突，对同分层扩展为 100% 检查。抽验通过只用于确认自动规则可靠；内容不同且未抽中的新卷仍保持候选，不标成逐份人工验证。

## 固定步骤

1. 运行 `python3 scripts/audit_temp_v2.py --with-pages`。该步只读，记录原路径、SHA-256、页数、保守的试卷身份和主库候选映射。省份目录仅表示使用范围，不能把全国卷拆成多份省级卷。
2. 身份映射或主库状态变化时才重跑 `python3 scripts/review_temp_v2_matches.py`（需 `pypdf`；Codex 环境使用工作区自带 Python）。只有页数与完整提取文本均一致，且主库记录是 `status!=verified + local-upload + license_status=unknown` 时，才进入安全替换候选。文本相似度只用于排序，不是相同证明。
3. 运行 `python3 scripts/sample_temp_v2_review.py --rate 0.02`，仅渲染抽样的首页、一个中间页和末页。检查试卷身份、题号/图表连续性、结束位置以及是否混入答案/解析/引流内容。不读整批 PDF。
4. 在 `scripts/apply_temp_v2_replacements.py` 登记显式决策。替换同时锁定旧/新哈希；新增和外部候选落地锁定新哈希、目标路径和完整核验说明。先干跑，再执行 `python3 scripts/apply_temp_v2_replacements.py --apply`。不从 `temp/` 批量导入。
5. 重新生成审计和短状态，再运行全库校验：

```bash
python3 scripts/audit_temp_v2.py --with-pages
python3 scripts/review_temp_v2_matches.py
python3 scripts/sample_temp_v2_review.py --rate 0.02
python3 scripts/temp_v2_status.py --write docs/temp-v2-status.md
python3 scripts/stats.py --check
python3 scripts/stats.py --write docs/coverage.md
python3 scripts/stats.py --write-readme README.md
python3 scripts/stats.py --write-index docs/papers-index.md
python3 scripts/stats.py --write-year-index docs/year-index.md
python3 scripts/stats.py --write-region-index docs/region-index.md
python3 scripts/stats.py --write-subject-year-matrix docs/subject-year-matrix.md
python3 scripts/audit_pdf_integrity.py --write docs/pdf-integrity.md
python3 -m unittest discover -s tests -v
python3 scripts/clean_temp_v2_cache.py --apply
```

## 对话与工作记忆

- 后续任务先读 [temp-v2-status.md](temp-v2-status.md)，再按需读审计 CSV 的少量行；不在对话中长期附加 8 GB 候选集或整份报告。
- 一次只处理一个可验证批次，临时渲染放在 `tmp/pdfs/`，不提交。每批结束立即运行 `python3 scripts/clean_temp_v2_cache.py --apply`；长期只保留抽样清单、哈希和结论。
- 每次交接只需报告：处理的 `record_id`、新旧 SHA-256、内容结论、验证命令和剩余队列计数。
