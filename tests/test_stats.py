import importlib.util
import sys
import tempfile
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

    def test_traceability_audit_distinguishes_local_provenance(self):
        web = {"status": "indexed", "material_type": "完整试卷", "source_url": "https://example.test/paper", "year": "2024", "source_type": "official", "license_status": "permitted"}
        local = {"status": "indexed", "material_type": "完整试卷", "source_url": "local://temp/paper.pdf", "year": "2024", "source_type": "local-upload", "license_status": "unknown"}
        summary = audit_traceability.summarize([web, local])
        self.assertEqual(summary["source_scope"]["公开 URL"], 1)
        self.assertEqual(summary["source_scope"]["仅本地导入来源"], 1)

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
        self.assertEqual(apply_content_review.review_action("unrelated-record"), "keep")


if __name__ == "__main__":
    unittest.main()
