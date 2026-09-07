import unittest

from scripts.cokb.model import CodeConcept, MappingAssertion, MappingLevel
from scripts.cokb.reasoner import COKBReasoner


def mapping(source_label, target_label):
    return MappingAssertion(
        source=CodeConcept("ICD10WHO", "X1", source_label),
        target=CodeConcept("ICD11", "Y1", target_label),
        evidence_source="test-graph",
    )


class ReasonerTests(unittest.TestCase):
    def setUp(self):
        self.reasoner = COKBReasoner()

    def test_exact_rule(self):
        result = self.reasoner.assess(mapping("Chronic gingivitis", "chronic gingivitis"))
        self.assertEqual(result.level, MappingLevel.EXACT)
        self.assertEqual(result.proof.rule_id, "R-EXACT-LABEL")

    def test_conflict_rule(self):
        result = self.reasoner.assess(mapping("Chronic gingivitis", "Acute gingivitis"))
        self.assertEqual(result.level, MappingLevel.CONFLICTING)

    def test_specificity_rule(self):
        result = self.reasoner.assess(mapping("Gingivitis", "Chronic gingivitis"))
        self.assertEqual(result.level, MappingLevel.PARTIAL)

    def test_generalized_rule(self):
        result = self.reasoner.assess(
            mapping("Infection due to other mycobacteria", "Infection, unspecified")
        )
        self.assertEqual(result.level, MappingLevel.PARTIAL)

    def test_unassessed_is_explicit(self):
        result = self.reasoner.assess(mapping("Acne", "Heart failure"))
        self.assertEqual(result.level, MappingLevel.UNASSESSED)
        self.assertEqual(result.proof.rule_id, "R-INSUFFICIENT-EVIDENCE")


if __name__ == "__main__":
    unittest.main()
