# DOCX 完整性审计

本页由 `python3 scripts/audit_docx_integrity.py --write docs/docx-integrity.md` 自动生成。
脚本只读检查 DOCX 的 Office ZIP 容器、内容清单和 Word 主文档 XML；它不验证版式、题目真实性、卷种或再发布许可。

## 总览

- 已检查 DOCX：**87**
- 结构完整：**87**
- 结构异常：**0**

## 按资料类别的结构完整 DOCX

| 资料类别 | 数量 |
| --- | ---: |
| 完整试卷 | 42 |
| 附属资料 | 41 |
| 片段资料 | 4 |

> 当前所有本地 DOCX 均可作为完整 Office 文档容器读取，并包含 Word 主文档 XML。
