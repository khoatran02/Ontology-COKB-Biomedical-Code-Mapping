import unittest

from scripts.cokb.evaluation import evaluate_label_pairs


class EvaluationTests(unittest.TestCase):
    def test_reports_coverage_separately_from_accuracy(self):
        result = evaluate_label_pairs(
            [
                {
                    "Input": {"original_label": "Chronic gingivitis", "mapped_label": "chronic gingivitis"},
                    "output": "A",
                },
                {
                    "Input": {"original_label": "Acne", "mapped_label": "Heart failure"},
                    "output": "C",
                },
            ]
        )
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["unassessed_count"], 1)
        self.assertEqual(result["coverage"], 0.5)
        self.assertEqual(result["overall_accuracy"], 0.5)
        self.assertEqual(result["accuracy_when_assessed"], 1.0)


if __name__ == "__main__":
    unittest.main()
