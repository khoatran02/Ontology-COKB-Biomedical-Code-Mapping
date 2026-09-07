import unittest
from pathlib import Path

from scripts.cokb.xlsx import read_first_sheet_records


ROOT = Path(__file__).resolve().parents[1]


class XlsxTests(unittest.TestCase):
    def test_reads_existing_gold_dataset_without_pandas(self):
        records = read_first_sheet_records(
            ROOT / "gold_datasets" / "mapping_level" / "code_pair_mapping_level__gold_standard__reasoning.xlsx"
        )
        self.assertEqual(len(records), 500)
        self.assertEqual(set(records[0]), {"Label", "Input", "output"})
        self.assertIn(records[0]["output"], {"A", "B", "C"})


if __name__ == "__main__":
    unittest.main()
