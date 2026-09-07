import unittest

from scripts.cokb.importer import repository_from_solutions


class Term:
    def __init__(self, value):
        self.value = value


class ImporterTests(unittest.TestCase):
    def test_converts_and_deduplicates_query_solutions(self):
        solution = {
            "sourceCode": Term("K05.1"),
            "sourceLabel": Term("Chronic gingivitis"),
            "targetCode": Term("DA0B.Y"),
            "targetLabel": Term("Chronic gingivitis"),
        }
        repository = repository_from_solutions(
            [solution, solution],
            source_system="ICD10WHO",
            target_system="ICD11",
            evidence_source="test-graph",
        )
        self.assertEqual(len(repository.mappings), 1)
        self.assertTrue(repository.validate().conforms)
        assessment = repository.infer()[0]
        self.assertEqual(assessment.level.value, "A")


if __name__ == "__main__":
    unittest.main()
