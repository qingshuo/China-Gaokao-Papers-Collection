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

本地 PDF 与 DOCX 文件还会在 `python3 scripts/stats.py --check` 中检查文件头是否与扩展名相符；这能防止下载错误页或损坏文件仅靠扩展名进入目录。

`python3 scripts/audit_pdf_integrity.py --write docs/pdf-integrity.md` 进一步用 PDF 解析器检查本地 PDF 是否可打开，并将页数不超过一页的主卷列为人工复核候选。

`python3 scripts/audit_docx_integrity.py --write docs/docx-integrity.md` 只读检查本地 DOCX 是否可作为 Office ZIP 容器打开、是否有内容清单和 Word 主文档 XML；这能发现压缩包损坏或误命名文件。

### 官方入口登记

`data/official-portals.csv` 是教育部教育考试院和省级教育考试机构的优先核查入口。它不等同于试卷来源，也不表示站点提供下载或已授权再发布；具体文件必须另行记录到 `source_url`。

### 官方身份佐证

`data/official-evidence.csv` 将一条试卷记录关联到教育考试机构的试题评析、公告、目录或官方下载页。`identity_scope=full_target` 表示页面可直接确认同一考试、卷种和学科；`context_only` 仅表明同年同批次的考试背景，不能用于确认该文件或计入卷制覆盖。它与 `source_url` 分离：前者用来佐证考试身份，后者记录文件实际来自何处。官方页面没有提供原卷文件时，不能据此将来源、授权或内容状态标为已核验。

### 卷制目标

`data/paper-targets.csv` 是独立于文件版本的卷制清单。一个目标由年份、地区/使用范围、卷种和科目界定，可关联一个或多个 `record_id` 与官方身份佐证。尚未收录文件的目标也应保留在此表；因此[`target-coverage.md`](target-coverage.md)只计算已声明目标的缺口，而不会将仓库文件数误称为全国完成率。

`data/target-evidence.csv` 保存直接关联到卷制目标的官方身份佐证，所有记录必须使用 `identity_scope=full_target`。它解决“官方页面已确认存在某卷、但尚未找到原卷文件”的情形；同样不表示文件来源或再发布许可。

### 用卷范围线索

`data/usage-scope-leads.csv` 保存社区维护的用卷范围表所提供的待核查线索。它可帮助发现某年某科可能存在的卷制、构建按省份的导航，但不属于官方身份佐证、试卷文件来源或再发布许可。可选的 `linked_record_ids` 仅关联当前已收录文件版本，用于公开“已找到文件 / 仍有版本冲突 / 尚未找到文件”的状态；它不证明这些文件对应官方卷制。只有取得教育考试机构原始公告、下载页或试题评析后，才可将对应项目加入 `data/paper-targets.csv` 的官方佐证目标。
