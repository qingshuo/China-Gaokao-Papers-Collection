# 项目说明

中国高考试卷资料库按年份、地区、学科和试卷类型整理公开可访问的高考试卷。仓库保存可追溯的元数据、来源链接和文件校验值，方便检索、核对和持续补充。

## 目录结构

```text
papers/              试卷文件
data/exams.csv       正式试卷索引（唯一事实源）
data/sources.csv     外部项目和候选来源
data/official-portals.csv 教育考试机构入口登记
data/official-evidence.csv 官方考试身份佐证
data/paper-targets.csv 已声明的实际卷制目标
config/regions.csv   省级行政区清单
scripts/stats.py     数据校验、统计和索引生成
scripts/audit_duplicates.py 生成候选重复的人工核验队列
scripts/audit_traceability.py 生成来源可追溯性审计
scripts/normalize_paper_layout.py 将旧来源目录迁入统一布局
scripts/normalize_national_regions.py 纠正明确全国卷的地区与目录
scripts/apply_content_review.py 应用经过内容核验的去重与分类结论
scripts/target_coverage.py 校验卷制目标并生成缺口报告
docs/papers-index.md 自动生成的试卷索引
docs/year-index.md   自动生成的按年份索引
docs/region-index.md 自动生成的按地区索引
docs/candidate-duplicates.md 自动生成的候选重复核验队列
docs/traceability.md 来源可追溯性审计
docs/local-only-sources.md 本地导入来源的补充队列
docs/official-evidence.md 官方身份佐证索引
docs/official-portals.md 省级教育考试机构官方渠道核查索引
docs/target-coverage.md 已声明卷制目标的覆盖与缺口
docs/content-review.md 已执行内容审查的依据与结论
docs/coverage.md     自动生成的覆盖统计
```

## 收录状态

- `discovered`：已发现线索，尚未整理文件。
- `indexed`：文件和元数据已进入索引，但内容可能仍待人工核验。
- `verified`：内容、来源和版本已经人工核验。
- `withdrawn`：记录已撤回，不计入有效覆盖。

`license_status=unknown` 表示上游没有提供清晰的许可信息，不代表文件可以自由再分发或商用。具体归属见 [`THIRD-PARTY-NOTICES.md`](../THIRD-PARTY-NOTICES.md)。

## 更新索引

项目使用 Python 3.10 或更高版本，不依赖第三方包：

```bash
python3 scripts/stats.py --check
python3 scripts/stats.py --write docs/coverage.md
python3 scripts/stats.py --write-readme README.md
python3 scripts/stats.py --write-index docs/papers-index.md
python3 scripts/stats.py --write-year-index docs/year-index.md
python3 scripts/stats.py --write-region-index docs/region-index.md
python3 scripts/stats.py --write-official-evidence-index docs/official-evidence.md
python3 scripts/stats.py --write-official-portals-index docs/official-portals.md
python3 scripts/target_coverage.py --check
python3 scripts/target_coverage.py --write docs/target-coverage.md
python3 scripts/audit_duplicates.py --write docs/candidate-duplicates.md
python3 scripts/audit_traceability.py --write docs/traceability.md
python3 scripts/audit_traceability.py --write-local-only-index docs/local-only-sources.md
python3 scripts/normalize_paper_layout.py --apply
python3 scripts/normalize_national_regions.py --apply
python3 scripts/apply_content_review.py --apply
python3 -m unittest discover -s tests -v
```

## 收录原则

- 每条记录必须包含稳定的来源 URL 和授权状态；本地文件还必须包含 SHA-256。
- 扫描件、答案、解析和不同卷别分别建记录，避免混合版本。
- 对来源不清、文件损坏或真实性存疑的资料，只登记候选来源，不标记为已核验。
- 收到权利人通知后，将及时核查并撤回或替换相关文件。

## 数据与许可

项目脚本和文档按 MIT 许可发布。试卷、图片、答案和第三方资料的版权及使用条件以各自来源和权利人声明为准。

详细字段定义见 [数据字典](data-dictionary.md)，补充资料请阅读 [贡献指南](../CONTRIBUTING.md)。
