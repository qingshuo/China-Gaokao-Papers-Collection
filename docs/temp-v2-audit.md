# temp 版本 2 审计

本页由 `python3 scripts/audit_temp_v2.py --with-pages` 生成。审计不会复制、移动或删除任何试卷。
省份目录只代表资料提供者标注的使用范围；名称明确的全国、新课标或新高考卷统一按全国卷候选处理。`same_identity_existing` 只是候选映射，替换前仍须比较题干、页数和版面。

## 总览

| 结果 | 数量 |
| --- | ---: |
| exact_existing_hash | 0 |
| same_identity_existing | 431 |
| temp_identity_duplicate | 2990 |
| new_candidate | 1581 |
| ambiguous_scope | 17 |

完整逐文件清单见 [temp-v2-audit.csv](temp-v2-audit.csv)，其中含原始相对路径、SHA-256、页数和候选替换记录。
