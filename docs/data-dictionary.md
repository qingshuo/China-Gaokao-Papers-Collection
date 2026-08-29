# 数据字典

`data/exams.csv` 是项目的唯一事实源，每行描述一个可区分的试卷版本。

| 字段 | 含义 |
| --- | --- |
| `record_id` | 稳定且唯一的记录标识 |
| `year` | 高考年份，历史收录从 1977 年开始 |
| `region` | 省级区域代码，使用 `config/regions.csv`；全国统一卷填 `全国` |
| `paper_type` | 试卷类型，如全国卷、新高考 I 卷或地方卷 |
| `subject` | 科目，如语文、数学、英语、物理 |
| `title` | 人类可读的完整名称 |
| `source_url` | 原始来源或授权发布页面 |
| `source_type` | `official`、`github`、`archive` 或其他明确来源类型 |
| `license_status` | `permitted`、`unknown`、`restricted` 或 `withdrawn` |
| `availability` | `none`（只有线索）、`external`（外部可访问）或 `local`（文件在仓库） |
| `status` | `planned`、`discovered`、`indexed`、`verified`、`withdrawn` |
| `local_path` | `availability=local` 时的仓库相对路径 |
| `sha256` | `availability=local` 时必填的 SHA-256 校验值，用于发现内容被替换 |
| `notes` | 核验、授权和版本差异说明 |

### 省份范围

`config/regions.csv` 收录中国大陆 31 个省级行政区。全国统一试卷不是省份，因此用单独的 `全国` 值表示，统计时不会把它错误展开成 31 份。

### 官方入口登记

`data/official-portals.csv` 是教育部教育考试院和省级教育考试机构的优先核查入口。它不等同于试卷来源，也不表示站点提供下载或已授权再发布；具体文件必须另行记录到 `source_url`。
