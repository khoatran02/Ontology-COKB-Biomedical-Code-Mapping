import unittest

from scripts.cokb.operators import (
    find_explicit_conflicts,
    labels_are_equivalent,
    normalize_code,
    normalize_label,
)


class OperatorTests(unittest.TestCase):
    def test_normalize_code(self):
        self.assertEqual(normalize_code(" k05.1 "), "K05.1")

    def test_normalize_label_handles_domain_aliases(self):
        self.assertEqual(normalize_label("Acute renal failure"), "acute kidney failure")
        self.assertTrue(labels_are_equivalent("Acute renal failure", "acute kidney failure"))

    def test_detects_explicit_conflict(self):
        conflicts = find_explicit_conflicts(
            "Gastric ulcer without hemorrhage",
            "Acute haemorrhagic gastric ulcer",
        )
        self.assertIn("hemorrhagic <> without hemorrhage", conflicts)


if __name__ == "__main__":
    unittest.main()
