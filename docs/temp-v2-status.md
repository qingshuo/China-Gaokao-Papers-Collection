# temp 版本 2 处理状态

这是与对话无关的短期工作记忆。后续处理先读本页与 `temp-v2-workflow.md`，不要把整份 PDF 或大型 CSV 装入对话上下文。

## 当前快照

| 指标 | 数量 |
| --- | ---: |
| temp v2 PDF | 5019 |
| 主库本地完整试卷 | 925 |
| 已验证本地完整试卷 | 108 |
| 仍未验证的本地上传主卷 | 105 |
| 显式替换决策（已应用 / 登记） | 82 / 82 |
| 显式新增决策（已应用 / 登记） | 25 / 25 |
| 外部候选落地（已应用 / 登记） | 1 / 1 |

## 审计队列

| 结果 | 数量 |
| --- | ---: |
| `exact_existing_hash` | 140 |
| `same_identity_existing` | 366 |
| `temp_identity_duplicate` | 2964 |
| `new_candidate` | 1532 |
| `ambiguous_scope` | 17 |

## 内容比对队列

| 结果 | 数量 |
| --- | ---: |
| `full_text_and_page_match` | 30 |
| `likely_same_content_layout_difference` | 10 |
| `content_or_page_difference` | 181 |
| `text_unavailable_or_too_short` | 163 |

报告中仍标记为安全替换候选：**0**。

## 分层抽验

共 **68** 份；待复核 **68**，通过 **0**，失败 **0**。

当前没有待应用的显式决策。

生成命令：`python3 scripts/temp_v2_status.py --write docs/temp-v2-status.md`
