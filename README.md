# 中国高考试卷资料库

按年份、省份、科目和试卷类型整理高考试卷的开放索引项目。项目优先保存可追溯的元数据和来源链接；只有在确认拥有再发布权限后，才把文件放入仓库。

## 当前状态

截至当前版本，仓库已归档 230 份 PDF：105 份数学卷和 125 份物理卷。语文、英语、地理的候选文档来源已登记，但因许可证未知暂未复制。已发现的外部线索见 [`data/sources.csv`](data/sources.csv)，正式收录记录见 [`data/exams.csv`](data/exams.csv)。运行统计脚本后，报告会写入 [`docs/coverage.md`](docs/coverage.md)。第三方归属说明见 [`THIRD-PARTY-NOTICES.md`](THIRD-PARTY-NOTICES.md)。

```text
data/exams.csv       正式试卷索引（唯一事实源）
data/sources.csv     外部项目和候选来源，不代表已取得授权
config/regions.csv   省级行政区清单
scripts/stats.py     数据校验与覆盖统计
docs/coverage.md     自动生成的统计报告
```

## 快速开始

需要 Python 3.10 或更高版本，不需要第三方依赖：

```bash
python3 scripts/stats.py --check
python3 scripts/stats.py --write docs/coverage.md
python3 -m unittest discover -s tests -v
```

## 收录原则

- 每条记录必须能回溯到来源 URL，并注明来源类型、可用性和授权状态。
- `discovered` 只表示发现了线索，`indexed` 表示已整理元数据，`verified` 才表示已核验内容和来源。
- `license_status=unknown` 的文件不复制到仓库；收到权利人通知后立即处理下架或替换链接。
- 扫描件、答案、解析可以分别建记录，避免把不同版本混成一条。
- 文件命名建议为 `papers/<year>/<region>/<subject>/<paper_type>.<ext>`，路径写入 `local_path`。

## 如何新增记录

1. 复制 [`data/exams.csv`](data/exams.csv) 中的表头，填写一条完整记录。
2. 使用 `python3 scripts/stats.py --check` 检查字段、年份和状态值。
3. 运行 `python3 scripts/stats.py --write docs/coverage.md` 更新报告。
4. 提交来源页面、授权说明和必要的校验信息，便于审核。

## 现有公开项目

GitHub 上已有一些有价值但范围不完整的项目，例如 [shaodongtang/gaokao_exam](https://github.com/shaodongtang/gaokao_exam)、[ajsadhotmail/2024-China-Gaokao-Math](https://github.com/ajsadhotmail/2024-China-Gaokao-Math)、[fihyer/NCEE](https://github.com/fihyer/NCEE) 和 [xihong-m/gaokao-math](https://github.com/xihong-m/gaokao-math)。本项目只记录它们作为线索，不重新分发其内容，也不替它们声明授权。

## 许可

项目中的脚本和文档按 MIT 许可发布。试卷、图片、答案和第三方链接的版权及使用条件以各自权利人和来源页面为准。
