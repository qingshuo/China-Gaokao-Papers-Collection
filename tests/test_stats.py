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


if __name__ == "__main__":
    unittest.main()
