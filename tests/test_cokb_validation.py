import unittest

from scripts.cokb.model import CodeConcept, MappingAssertion
from scripts.cokb.validation import validate_mappings


class ValidationTests(unittest.TestCase):
    def test_missing_label_is_rejected(self):
        invalid = MappingAssertion(
            source=CodeConcept("ICD10CM", "K05.1", ""),
            target=CodeConcept("ICD11", "DA0B.Y", "Chronic gingivitis"),
            evidence_source="test",
        )
        report = validate_mappings([invalid])
        self.assertFalse(report.conforms)
        self.assertIn("COKB_REQUIRED_VALUE", {issue.code for issue in report.issues})

    def test_duplicate_mapping_id_is_rejected(self):
        first = MappingAssertion(
            mapping_id="duplicate",
            source=CodeConcept("ICD10CM", "A", "A"),
            target=CodeConcept("ICD11", "B", "B"),
            evidence_source="test",
        )
        second = MappingAssertion(
            mapping_id="duplicate",
            source=CodeConcept("ICD10CM", "C", "C"),
            target=CodeConcept("ICD11", "D", "D"),
            evidence_source="test",
        )
        self.assertFalse(validate_mappings([first, second]).conforms)


if __name__ == "__main__":
    unittest.main()
