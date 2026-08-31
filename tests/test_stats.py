import importlib.util
import sys
import tempfile
import unittest
import zipfile
from collections import Counter
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "stats.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("stats", SCRIPT)
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)

DEDUPLICATE_SCRIPT = Path(__file__).parents[1] / "scripts" / "deduplicate_formats.py"
DEDUPLICATE_SPEC = importlib.util.spec_from_file_location("deduplicate_formats", DEDUPLICATE_SCRIPT)
deduplicate_formats = importlib.util.module_from_spec(DEDUPLICATE_SPEC)
DEDUPLICATE_SPEC.loader.exec_module(deduplicate_formats)

AUDIT_SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_duplicates.py"
AUDIT_SPEC = importlib.util.spec_from_file_location("audit_duplicates", AUDIT_SCRIPT)
audit_duplicates = importlib.util.module_from_spec(AUDIT_SPEC)
AUDIT_SPEC.loader.exec_module(audit_duplicates)

TRACEABILITY_SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_traceability.py"
TRACEABILITY_SPEC = importlib.util.spec_from_file_location("audit_traceability", TRACEABILITY_SCRIPT)
audit_traceability = importlib.util.module_from_spec(TRACEABILITY_SPEC)
TRACEABILITY_SPEC.loader.exec_module(audit_traceability)

LAYOUT_SCRIPT = Path(__file__).parents[1] / "scripts" / "normalize_paper_layout.py"
LAYOUT_SPEC = importlib.util.spec_from_file_location("normalize_paper_layout", LAYOUT_SCRIPT)
normalize_paper_layout = importlib.util.module_from_spec(LAYOUT_SPEC)
LAYOUT_SPEC.loader.exec_module(normalize_paper_layout)

NATIONAL_REGIONS_SCRIPT = Path(__file__).parents[1] / "scripts" / "normalize_national_regions.py"
NATIONAL_REGIONS_SPEC = importlib.util.spec_from_file_location("normalize_national_regions", NATIONAL_REGIONS_SCRIPT)
normalize_national_regions = importlib.util.module_from_spec(NATIONAL_REGIONS_SPEC)
NATIONAL_REGIONS_SPEC.loader.exec_module(normalize_national_regions)

CONTENT_REVIEW_SCRIPT = Path(__file__).parents[1] / "scripts" / "apply_content_review.py"
CONTENT_REVIEW_SPEC = importlib.util.spec_from_file_location("apply_content_review", CONTENT_REVIEW_SCRIPT)
apply_content_review = importlib.util.module_from_spec(CONTENT_REVIEW_SPEC)
CONTENT_REVIEW_SPEC.loader.exec_module(apply_content_review)

TARGET_COVERAGE_SCRIPT = Path(__file__).parents[1] / "scripts" / "target_coverage.py"
TARGET_COVERAGE_SPEC = importlib.util.spec_from_file_location("target_coverage", TARGET_COVERAGE_SCRIPT)
target_coverage = importlib.util.module_from_spec(TARGET_COVERAGE_SPEC)
TARGET_COVERAGE_SPEC.loader.exec_module(target_coverage)

BINARY_AUDIT_SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_binary_duplicates.py"
BINARY_AUDIT_SPEC = importlib.util.spec_from_file_location("audit_binary_duplicates", BINARY_AUDIT_SCRIPT)
binary_audit = importlib.util.module_from_spec(BINARY_AUDIT_SPEC)
BINARY_AUDIT_SPEC.loader.exec_module(binary_audit)

AUTHENTICITY_AUDIT_SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_authenticity.py"
AUTHENTICITY_AUDIT_SPEC = importlib.util.spec_from_file_location("audit_authenticity", AUTHENTICITY_AUDIT_SCRIPT)
authenticity_audit = importlib.util.module_from_spec(AUTHENTICITY_AUDIT_SPEC)
AUTHENTICITY_AUDIT_SPEC.loader.exec_module(authenticity_audit)

PDF_INTEGRITY_SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_pdf_integrity.py"
PDF_INTEGRITY_SPEC = importlib.util.spec_from_file_location("audit_pdf_integrity", PDF_INTEGRITY_SCRIPT)
pdf_integrity = importlib.util.module_from_spec(PDF_INTEGRITY_SPEC)
PDF_INTEGRITY_SPEC.loader.exec_module(pdf_integrity)

DOCX_INTEGRITY_SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_docx_integrity.py"
DOCX_INTEGRITY_SPEC = importlib.util.spec_from_file_location("audit_docx_integrity", DOCX_INTEGRITY_SCRIPT)
docx_integrity = importlib.util.module_from_spec(DOCX_INTEGRITY_SPEC)
DOCX_INTEGRITY_SPEC.loader.exec_module(docx_integrity)

USAGE_SCOPE_LEADS_SCRIPT = Path(__file__).parents[1] / "scripts" / "usage_scope_leads.py"
USAGE_SCOPE_LEADS_SPEC = importlib.util.spec_from_file_location("usage_scope_leads", USAGE_SCOPE_LEADS_SCRIPT)
usage_scope_leads = importlib.util.module_from_spec(USAGE_SCOPE_LEADS_SPEC)
USAGE_SCOPE_LEADS_SPEC.loader.exec_module(usage_scope_leads)

IMPORT_DEEKUR_SCRIPT = Path(__file__).parents[1] / "scripts" / "import_deekur_math.py"
IMPORT_DEEKUR_SPEC = importlib.util.spec_from_file_location("import_deekur_math", IMPORT_DEEKUR_SCRIPT)
import_deekur_math = importlib.util.module_from_spec(IMPORT_DEEKUR_SPEC)
IMPORT_DEEKUR_SPEC.loader.exec_module(import_deekur_math)


class StatsTests(unittest.TestCase):
    def test_empty_catalog_is_valid(self):
        self.assertEqual(stats.validate_catalog([], {"BJ"}), [])

    def test_official_portals_require_each_region_once(self):
        rows = [
            {"region": "全国", "agency": "考试机构", "portal_url": "https://example.test", "portal_status": "checked"},
            {"region": "BJ", "agency": "北京考试机构", "portal_url": "https://example.test/bj", "portal_status": "announcement_only"},
        ]
        self.assertEqual(stats.validate_official_portals(rows, {"BJ"}), [])
        self.assertTrue(stats.validate_official_portals(rows[:-1], {"BJ"}))

    def test_official_evidence_requires_known_record_and_https_url(self):
        row = {
            "evidence_id": "neea-2021", "record_id": "paper-1", "evidence_type": "official_analysis",
            "evidence_url": "https://example.test/evidence", "issuer": "考试机构",
        }
        self.assertEqual(stats.validate_official_evidence([row], {"paper-1"}), [])
        self.assertTrue(stats.validate_official_evidence([{**row, "record_id": "missing"}], {"paper-1"}))
        self.assertTrue(stats.validate_official_evidence([{**row, "evidence_url": "http://example.test"}], {"paper-1"}))

    def test_local_record_requires_path(self):
        row = {field: "value" for field in stats.REQUIRED_FIELDS}
        row.update({"year": "2024", "region": "BJ", "status": "indexed", "availability": "local", "local_path": ""})
        errors = stats.validate_catalog([row], {"BJ"})
        self.assertTrue(any("requires local_path" in error for error in errors))

    def test_local_file_signature_validation_detects_mismatched_pdf_and_docx(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            bad_pdf = root / "paper.pdf"
            bad_pdf.write_bytes(b"not-a-pdf")
            bad_docx = root / "paper.docx"
            bad_docx.write_bytes(b"not-a-docx")
            good_pdf = root / "paper-good.pdf"
            good_pdf.write_bytes(b"%PDF-1.7")
            self.assertIn("PDF extension", stats.file_format_error(bad_pdf) or "")
            self.assertIn("DOCX extension", stats.file_format_error(bad_docx) or "")
            self.assertIsNone(stats.file_format_error(good_pdf))

    def test_only_local_records_require_sha256(self):
        row = {field: "value" for field in stats.REQUIRED_FIELDS}
        row.update({"year": "2024", "region": "BJ", "status": "discovered", "availability": "external", "sha256": ""})
        self.assertEqual(stats.validate_catalog([row], {"BJ"}), [])
        row["availability"] = "local"
        row["local_path"] = "papers/example.pdf"
        errors = stats.validate_catalog([row], {"BJ"})
        self.assertTrue(any("requires sha256" in error for error in errors))

    def test_summary_excludes_withdrawn(self):
        rows = [
            {"year": "2024", "region": "BJ", "subject": "数学", "status": "verified", "availability": "local"},
            {"year": "2023", "region": "SH", "subject": "语文", "status": "withdrawn", "availability": "external"},
        ]
        summary = stats.summarize(rows, [{"name": "source"}])
        self.assertEqual(summary["active_records"], 1)
        self.assertEqual(summary["verified"], 1)
        self.assertEqual(summary["years"], ["2024"])

    def test_readme_uses_current_complete_paper_counts(self):
        rows = [
            {"year": "2024", "region": "BJ", "subject": "数学", "status": "indexed", "availability": "local"},
            {"year": "2024", "region": "BJ", "subject": "数学", "status": "indexed", "availability": "local", "material_type": "附属资料"},
            {"year": "2023", "region": "SH", "subject": "语文", "status": "indexed", "availability": "local"},
        ]
        readme = stats.render_readme(stats.summarize(rows, []))
        self.assertIn("**2 份完整试卷**", readme)
        self.assertIn("附属资料 **1 份**", readme)
        self.assertIn("| 2024 | 1 |", readme)
        self.assertIn("PDF 完整性审计", readme)
        self.assertIn("DOCX 完整性审计", readme)

    def test_readme_excludes_external_papers_from_local_index_counts(self):
        rows = [
            {"year": "2024", "region": "BJ", "subject": "数学", "status": "indexed", "availability": "local"},
            {"year": "2024", "region": "SH", "subject": "数学", "status": "discovered", "availability": "external"},
        ]
        readme = stats.render_readme(stats.summarize(rows, []))
        self.assertIn("**1 份完整试卷**", readme)
        self.assertIn("| 2024 | 1 |", readme)

    def test_subject_year_matrix_links_only_complete_local_papers(self):
        base = {"year": "2024", "status": "indexed", "availability": "local", "material_type": "完整试卷"}
        rows = [
            {**base, "subject": "数学"},
            {**base, "subject": "数学"},
            {**base, "subject": "物理"},
            {**base, "subject": "语文", "material_type": "附属资料"},
        ]
        matrix = stats.render_subject_year_matrix(rows)
        self.assertIn("[2](papers-index.md#2024-数学)", matrix)
        self.assertIn("[1](papers-index.md#2024-物理)", matrix)
        self.assertNotIn("2024-语文)", matrix)

    def test_usage_scope_leads_remain_community_not_official_evidence(self):
        row = {
            "lead_id": "community-2024-math", "year": "2024", "subject": "数学", "paper_type": "新高考I卷",
            "scope": "北京", "source_name": "community", "source_url": "https://example.test/usage.xlsx",
            "confidence": "community_unverified", "notes": "仅线索",
        }
        self.assertEqual(usage_scope_leads.validate_leads([row]), [])
        self.assertTrue(usage_scope_leads.validate_leads([{**row, "confidence": "official"}]))
        report = usage_scope_leads.render_markdown([row])
        self.assertIn("不是官方身份佐证", report)

    def test_usage_scope_lead_links_validate_catalog_identity_and_report_conflicts(self):
        lead = {
            "lead_id": "community-2024-math", "year": "2024", "subject": "数学", "paper_type": "新高考I卷",
            "scope": "北京", "source_name": "community", "source_url": "https://example.test/usage.xlsx",
            "confidence": "community_unverified", "linked_record_ids": "paper-1;paper-2", "notes": "仅线索",
        }
        records = {
            "paper-1": {"record_id": "paper-1", "year": "2024", "subject": "数学", "status": "indexed", "availability": "local", "material_type": "完整试卷", "local_path": "papers/first.pdf", "title": "版本一", "notes": "内容复核：差异，暂不合并"},
            "paper-2": {"record_id": "paper-2", "year": "2024", "subject": "数学", "status": "indexed", "availability": "local", "material_type": "完整试卷", "local_path": "papers/second.pdf", "title": "版本二", "notes": "内容复核：差异，暂不合并"},
        }
        self.assertEqual(usage_scope_leads.validate_leads([lead], records), [])
        report = usage_scope_leads.render_markdown([lead], records)
        self.assertIn("已收录 2 个冲突版本", report)
        self.assertIn("../papers/first.pdf", report)
        self.assertTrue(usage_scope_leads.validate_leads([{**lead, "linked_record_ids": "missing"}], records))

    def test_official_evidence_index_keeps_origin_and_identity_evidence_separate(self):
        paper = {
            "record_id": "paper-1", "year": "2024", "region": "BJ", "subject": "数学", "title": "北京数学",
            "availability": "local", "local_path": "papers/2024/BJ/数学/北京数学.pdf", "source_url": "https://mirror.test/paper",
        }
        evidence = {
            "evidence_id": "neea-2024", "record_id": "paper-1", "evidence_type": "official_analysis",
            "evidence_url": "https://official.test/analysis", "issuer": "教育考试院",
        }
        index = stats.render_official_evidence_index([evidence], {"paper-1": paper}, {"BJ": "北京"})
        self.assertIn("官方试题评析", index)
        self.assertIn("https://official.test/analysis", index)
        self.assertIn("../papers/2024/BJ/", index)

    def test_official_portals_index_displays_research_status(self):
        row = {
            "region": "BJ", "agency": "北京教育考试院", "portal_url": "https://example.test",
            "scope": "北京高考", "portal_status": "announcement_only", "notes": "只找到公告",
        }
        index = stats.render_official_portals_index([row], {"BJ": "北京"})
        self.assertIn("仅公告/评析", index)
        self.assertIn("[访问入口](https://example.test)", index)

    def test_target_coverage_keeps_declared_targets_separate_from_files(self):
        target = {
            "target_id": "target-1", "year": "2024", "region": "BJ", "subject": "数学",
            "paper_type": "北京卷", "title": "北京数学", "scope": "北京", "linked_record_ids": "paper-1",
            "official_evidence_ids": "evidence-1", "notes": "",
        }
        records = {"paper-1": {"status": "indexed", "availability": "local", "material_type": "完整试卷"}}
        evidence = {"evidence-1": {"record_id": "paper-1"}}
        self.assertEqual(target_coverage.validate_targets([target], {"paper-1": {**records["paper-1"], "year": "2024", "region": "BJ", "subject": "数学"}}, evidence, {"BJ"}), [])
        wrong_evidence = {"evidence-1": {"record_id": "another-paper"}}
        self.assertTrue(target_coverage.validate_targets([target], {"paper-1": {**records["paper-1"], "year": "2024", "region": "BJ", "subject": "数学"}}, wrong_evidence, {"BJ"}))
        self.assertEqual(target_coverage.target_state(target, records), "已入库")
        report = target_coverage.render_markdown([target], records, {"BJ": "北京"})
        self.assertIn("不能**代表全国所有高考试卷", report)
        self.assertIn("已入库", report)

    def test_target_level_official_evidence_can_confirm_an_uncollected_paper_target(self):
        target = {
            "target_id": "target-1", "year": "2024", "region": "BJ", "subject": "数学",
            "paper_type": "春考卷", "title": "北京春考数学", "scope": "北京", "linked_record_ids": "",
            "official_evidence_ids": "target-evidence-1", "notes": "",
        }
        evidence = {
            "evidence_id": "target-evidence-1", "target_id": "target-1", "evidence_type": "official_analysis",
            "evidence_url": "https://official.test/analysis", "issuer": "考试机构", "notes": "试题评析",
        }
        self.assertEqual(target_coverage.validate_target_evidence([evidence], {"target-1"}), [])
        self.assertEqual(target_coverage.validate_targets([target], {}, {}, {"BJ"}, {"target-evidence-1": evidence}), [])
        self.assertEqual(target_coverage.target_state(target, {}), "待收录")
        index = target_coverage.render_target_evidence_index([evidence], {"target-1": target}, {"BJ": "北京"})
        self.assertIn("原卷下载", index)
        self.assertIn("北京春考数学", index)

    def test_material_classification_preserves_complete_papers_with_answers(self):
        self.assertEqual(stats.classify_material({"paper_type": "答案", "title": "2024 高考数学（含答案）"}), "完整试卷")
        self.assertEqual(stats.classify_material({"paper_type": "答案", "title": "2024 高考数学答案"}), "附属资料")
        self.assertEqual(stats.classify_material({"paper_type": "解析版", "title": "2024 高考数学解析"}), "附属资料")
        self.assertEqual(stats.classify_material({"paper_type": "原卷", "title": "2025 高考河北化学实验题"}), "片段资料")
        self.assertEqual(stats.classify_material({"paper_type": "原卷", "title": "2025 江西选择性考试物理"}), "完整试卷")

    def test_main_index_excludes_supporting_materials(self):
        base = {
            "year": "2024", "region": "BJ", "subject": "数学", "status": "indexed",
            "availability": "local", "local_path": "papers/example.pdf", "paper_type": "原卷",
            "license_status": "permitted",
        }
        complete = {**base, "title": "完整试卷", "material_type": "完整试卷"}
        answer = {**base, "title": "答案", "material_type": "附属资料"}
        index = stats.render_papers_index([complete, answer], {"BJ": "北京"})
        self.assertIn("完整试卷", index)
        self.assertNotIn("](<../papers/example.pdf>)", index)
        self.assertNotIn("| [答案]", index)

    def test_year_and_region_indexes_exclude_supporting_materials(self):
        base = {
            "year": "2024", "region": "BJ", "subject": "数学", "status": "indexed",
            "availability": "local", "local_path": "papers/example.pdf", "paper_type": "原卷",
            "license_status": "permitted",
        }
        complete = {**base, "title": "完整试卷", "material_type": "完整试卷"}
        answer = {**base, "title": "答案", "material_type": "附属资料"}
        self.assertIn("完整试卷", stats.render_year_index([complete, answer], {"BJ": "北京"}))
        self.assertIn("完整试卷", stats.render_region_index([complete, answer], {"BJ": "北京"}))

    def test_index_labels_multi_region_national_paper(self):
        row = {
            "year": "2024", "region": "全国", "subject": "数学",
            "status": "indexed", "availability": "local", "title": "2024全国1(北京,上海)",
            "local_path": "papers/example.pdf", "paper_type": "普通高考",
            "license_status": "permitted",
        }
        index = stats.render_papers_index([row], {})
        self.assertIn("全国/多省", index)

    def test_index_exposes_reviewed_content_variants_without_claiming_other_rows_are_verified(self):
        base = {"status": "indexed", "availability": "local", "material_type": "完整试卷"}
        complete = {**base, "notes": "内容复核：与另一版本第 9 题多出一条背景句，暂不合并。"}
        conflict = {**base, "notes": "内容复核：与另一版本存在实质题干差异，暂不合并。"}
        ordinary = {**base, "notes": "用户导入"}
        self.assertEqual(stats.review_hint(complete), "优先版本；待官方核验")
        self.assertEqual(stats.review_hint(conflict), "题干冲突；待官方核验")
        self.assertEqual(stats.review_hint(ordinary), "—")

    def test_pdf_format_deduplication_requires_exact_catalog_identity(self):
        base = {
            "year": "2024", "region": "BJ", "subject": "数学", "paper_type": "原卷",
            "material_type": "完整试卷", "title": "北京数学", "availability": "local",
        }
        pdf = {**base, "local_path": "papers/2024/BJ/数学/北京数学.pdf"}
        docx = {**base, "local_path": "papers/2024/BJ/数学/北京数学.docx"}
        another_paper = {**base, "title": "北京数学另一卷", "local_path": "papers/2024/BJ/数学/另一卷.docx"}
        pairs = deduplicate_formats.pdf_format_duplicates([pdf, docx, another_paper], "2024")
        self.assertEqual(pairs, [(pdf, docx)])

    def test_duplicate_audit_groups_title_variants_without_deleting(self):
        base = {"year": "2025", "region": "BJ", "subject": "数学", "status": "indexed", "material_type": "完整试卷"}
        first = {**base, "title": "2025年北京高考数学"}
        second = {**base, "title": "2025北京"}
        different_paper = {**base, "title": "2025全国一卷数学"}
        groups = audit_duplicates.candidate_groups([first, second, different_paper])
        self.assertEqual([group[0] for group in groups], [("2025", "BJ", "数学", "北京")])
        self.assertEqual(groups[0][1], [first, second])

    def test_duplicate_audit_normalizes_ascii_new_gaokao_roman_numerals(self):
        base = {"year": "2021", "region": "全国", "subject": "数学", "status": "indexed", "material_type": "完整试卷"}
        first = {**base, "title": "2021新高考1(山东)"}
        second = {**base, "title": "2021年新高考I卷数学（原卷）"}
        groups = audit_duplicates.candidate_groups([first, second])
        self.assertEqual(len(groups), 1)

    def test_duplicate_audit_keeps_explicit_reviewed_conflicts_visible_when_titles_differ(self):
        base = {"year": "2024", "region": "TJ", "subject": "数学", "status": "indexed", "material_type": "完整试卷"}
        first = {**base, "record_id": "deekur-2024-47-math", "title": "2024天津", "notes": "内容复核：存在实质题干差异，暂不合并。"}
        second = {**base, "record_id": "temp-2024-数学-d7ffc6dab1af", "title": "天津数学-试题-p", "notes": "内容复核：存在实质题干差异，暂不合并。"}
        groups = audit_duplicates.candidate_groups([first, second])
        pending, reviewed = audit_duplicates.partition_groups(groups)
        self.assertEqual(pending, [])
        self.assertEqual(len(reviewed), 1)
        self.assertEqual({row["record_id"] for row in reviewed[0][1]}, {first["record_id"], second["record_id"]})

    def test_duplicate_audit_separates_reviewed_conflicts_from_pending_candidates(self):
        base = {"year": "2026", "region": "BJ", "subject": "数学", "status": "indexed", "material_type": "完整试卷"}
        conflict_a = {**base, "title": "2026北京", "notes": "内容复核：存在实质题干差异，暂不合并，待官方来源核验。"}
        conflict_b = {**base, "title": "数学北京卷", "notes": "内容复核：存在实质题干差异，暂不合并，待官方来源核验。"}
        pending_a = {**base, "year": "2025", "title": "2025北京", "notes": ""}
        pending_b = {**base, "year": "2025", "title": "2025年北京高考数学", "notes": ""}
        pending, reviewed = audit_duplicates.partition_groups(audit_duplicates.candidate_groups([conflict_a, conflict_b, pending_a, pending_b]))
        self.assertEqual(len(pending), 1)
        self.assertEqual(len(reviewed), 1)

    def test_deekur_historical_import_keeps_unicode_filename_and_assigns_nationwide_region(self):
        path = "普通高考/2016/2016全国2文(甘肃,青海,内蒙古,黑龙江,吉林,辽宁,海南,宁夏,新疆,西藏,陕西,重庆).pdf"
        row = import_deekur_math.build_rows("2016", [path], [{"code": "BJ", "name": "北京"}])[0]
        self.assertEqual(row["region"], "全国")
        self.assertEqual(Path(import_deekur_math.unquote(row["source_url"].removeprefix(import_deekur_math.RAW_ROOT))).name, Path(path).name)

    def test_deekur_historical_import_keeps_unresolved_scope_files_out_of_main_batch(self):
        paths = [
            "普通高考/1994/1994全国新科目组文.pdf",
            "普通高考/1994/1994旧科目组文.pdf",
        ]
        eligible, skipped = import_deekur_math.eligible_source_paths(paths)
        self.assertEqual(eligible, ["普通高考/1994/1994全国新科目组文.pdf"])
        self.assertEqual(skipped, ["普通高考/1994/1994旧科目组文.pdf"])

    def test_deekur_historical_import_requires_audited_title_year_correction(self):
        path = "普通高考/2007/2002大纲2文(黑龙江,吉林,贵州,新疆,内蒙古,青海,云南,西藏,甘肃).pdf"
        row = import_deekur_math.build_rows("2007", [path], [{"code": "BJ", "name": "北京"}])[0]
        self.assertEqual(row["title"], "2007大纲2文(黑龙江,吉林,贵州,新疆,内蒙古,青海,云南,西藏,甘肃)")
        self.assertIn("首页标题已人工核验为 2007 年", row["notes"])

    def test_deekur_historical_import_keeps_shared_guangdong_guangxi_paper_distinct_from_national(self):
        path = "普通高考/2003/2003广东,广西.pdf"
        row = import_deekur_math.build_rows("2003", [path], [{"code": "GD", "name": "广东"}, {"code": "GX", "name": "广西"}])[0]
        self.assertEqual(row["region"], "GD-GX")
        self.assertIn("文件名覆盖 广东、广西", row["notes"])
        row.update({"availability": "external", "local_path": "", "sha256": ""})
        self.assertEqual(stats.validate_catalog([row], {"GD", "GX"}), [])

    def test_deekur_historical_import_supports_other_shared_province_combinations(self):
        path = "普通高考/2002/2002广东,河南,江苏,广西.pdf"
        regions = [
            {"code": "GD", "name": "广东"}, {"code": "GX", "name": "广西"},
            {"code": "HA", "name": "河南"}, {"code": "JS", "name": "江苏"},
        ]
        row = import_deekur_math.build_rows("2002", [path], regions)[0]
        self.assertEqual(row["region"], "GD-GX-HA-JS")
        self.assertEqual(stats.region_label(row["region"], {item["code"]: item["name"] for item in regions}), "广东、广西、河南、江苏（共用卷）")

    def test_binary_audit_groups_only_identical_hashes_without_deletion(self):
        base = {
            "year": "2024", "region": "BJ", "subject": "数学", "status": "indexed", "availability": "local",
            "sha256": "a" * 64, "record_id": "one", "local_path": "papers/one.pdf", "title": "一", "material_type": "完整试卷",
        }
        same = {**base, "record_id": "two", "local_path": "papers/two.pdf"}
        distinct = {**base, "record_id": "three", "sha256": "b" * 64}
        withdrawn = {**base, "record_id": "four", "status": "withdrawn"}
        groups = binary_audit.exact_hash_groups([base, same, distinct, withdrawn])
        self.assertEqual(groups, [("a" * 64, [base, same])])

    def test_authenticity_audit_flags_only_main_library_risk_terms(self):
        main = {"status": "indexed", "material_type": "完整试卷", "title": "2024 高考数学模拟卷", "notes": ""}
        supporting = {**main, "material_type": "附属资料", "title": "2024 高考数学解析版"}
        findings = authenticity_audit.suspicious_complete_papers([main, supporting])
        self.assertEqual(findings, [(main, ["模拟"])])

    def test_pdf_integrity_extracts_page_count_from_pdfinfo_output(self):
        self.assertEqual(pdf_integrity.pages_from_pdfinfo("Title: test\nPages:          7\n"), 7)
        self.assertIsNone(pdf_integrity.pages_from_pdfinfo("Title: test\n"))

    def test_pdf_integrity_reports_reviewed_single_page_papers_separately(self):
        row = {"record_id": "paper-1", "year": "2024", "region": "BJ", "subject": "数学", "title": "北京数学", "local_path": "papers/paper.pdf"}
        report = pdf_integrity.render_markdown([], [], [(row, 1, "已视觉复核")], Counter({"完整试卷": 1}))
        self.assertIn("已复核的单页完整卷", report)
        self.assertIn("已视觉复核", report)

    def test_docx_integrity_requires_office_manifest_and_word_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "paper.docx"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("[Content_Types].xml", "<Types />")
                archive.writestr("word/document.xml", "<w:document />")
            self.assertIsNone(docx_integrity.inspect_docx(path))
            broken = Path(directory) / "broken.docx"
            broken.write_bytes(b"not a zip")
            self.assertIn("Office ZIP", docx_integrity.inspect_docx(broken) or "")

    def test_traceability_audit_distinguishes_local_provenance(self):
        web = {"status": "indexed", "material_type": "完整试卷", "source_url": "https://example.test/paper", "year": "2024", "source_type": "official", "license_status": "permitted"}
        local = {"status": "indexed", "material_type": "完整试卷", "source_url": "local://temp/paper.pdf", "year": "2024", "source_type": "local-upload", "license_status": "unknown"}
        summary = audit_traceability.summarize([web, local])
        self.assertEqual(summary["source_scope"]["公开 URL"], 1)
        self.assertEqual(summary["source_scope"]["仅本地导入来源"], 1)

    def test_local_only_source_queue_lists_only_complete_local_provenance(self):
        local = {
            "record_id": "local-1", "year": "2024", "region": "BJ", "subject": "数学", "paper_type": "北京卷",
            "title": "北京数学", "status": "indexed", "material_type": "完整试卷", "source_url": "local://temp/paper.pdf",
            "local_path": "papers/2024/BJ/数学/北京数学.pdf",
        }
        web = {**local, "record_id": "web-1", "source_url": "https://example.test/paper"}
        index = audit_traceability.render_local_only_index([local, web], {"BJ": "北京"})
        self.assertIn("local-1", index)
        self.assertNotIn("web-1", index)
        self.assertIn("../papers/2024/BJ/", index)

    def test_layout_normalization_moves_legacy_source_directories(self):
        row = {
            "availability": "local", "local_path": "papers/deekur/数学/2024/2024北京.pdf",
            "year": "2024", "region": "BJ", "subject": "数学", "sha256": "a" * 64,
        }
        with tempfile.TemporaryDirectory() as directory:
            parent = Path(directory) / "papers" / "2024" / "BJ" / "数学"
            self.assertEqual(
                normalize_paper_layout.unique_destination(parent, "2024北京.pdf", row["sha256"]),
                parent / "2024北京.pdf",
            )

    def test_national_region_normalization_requires_explicit_nationwide_title(self):
        nationwide = {"region": "GD", "title": "2024全国新高考卷", "availability": "local"}
        provincial = {"region": "GD", "title": "2024广东高考卷", "availability": "local"}
        self.assertTrue(normalize_national_regions.is_nationwide_paper(nationwide))
        self.assertFalse(normalize_national_regions.is_nationwide_paper(provincial))

    def test_content_review_only_applies_explicit_evidence_backed_actions(self):
        self.assertEqual(apply_content_review.review_action("deekur-2025-53-math"), "remove")
        self.assertEqual(apply_content_review.review_action("deekur-2025-physics-023"), "supplement")
        self.assertEqual(apply_content_review.review_action("temp-2025-物理-d1cb17271a18"), "partial")
        self.assertEqual(apply_content_review.review_action("temp-2021-数学-cd8daafb088b"), "supplement")
        self.assertEqual(apply_content_review.TITLE_UPDATES["temp-2021-数学-698c99e83f2e"], "2021年新高考I卷数学（原卷）")
        self.assertEqual(apply_content_review.REMOVE_IDS, apply_content_review.HISTORIC_REMOVED_IDS)
        self.assertEqual(apply_content_review.review_action("deekur-2021-21-math"), "remove")
        self.assertEqual(apply_content_review.review_action("unrelated-record"), "keep")


if __name__ == "__main__":
    unittest.main()
