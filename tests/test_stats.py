import importlib.util
import sys
import unittest
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

    def test_local_record_requires_path(self):
        row = {field: "value" for field in stats.REQUIRED_FIELDS}
        row.update({"year": "2024", "region": "BJ", "status": "indexed", "availability": "local", "local_path": ""})
        errors = stats.validate_catalog([row], {"BJ"})
        self.assertTrue(any("requires local_path" in error for error in errors))

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


if __name__ == "__main__":
    unittest.main()
