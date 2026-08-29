import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "stats.py"
SPEC = importlib.util.spec_from_file_location("stats", SCRIPT)
stats = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stats)


class StatsTests(unittest.TestCase):
    def test_empty_catalog_is_valid(self):
        self.assertEqual(stats.validate_catalog([], {"BJ"}), [])

    def test_local_record_requires_path(self):
        row = {field: "value" for field in stats.REQUIRED_FIELDS}
        row.update({"year": "2024", "region": "BJ", "status": "indexed", "availability": "local", "local_path": ""})
        errors = stats.validate_catalog([row], {"BJ"})
        self.assertTrue(any("requires local_path" in error for error in errors))

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

    def test_index_labels_multi_region_national_paper(self):
        row = {
            "year": "2024", "region": "全国", "subject": "数学",
            "status": "indexed", "availability": "local", "title": "2024全国1(北京,上海)",
            "local_path": "papers/example.pdf", "paper_type": "普通高考",
            "license_status": "permitted",
        }
        index = stats.render_papers_index([row], {})
        self.assertIn("全国/多省", index)


if __name__ == "__main__":
    unittest.main()
