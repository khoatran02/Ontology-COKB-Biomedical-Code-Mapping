import json
import tempfile
import unittest
from pathlib import Path

from scripts.cokb.repository import COKBRepository


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "examples" / "icd_mapping_sample.json"


class RepositoryTests(unittest.TestCase):
    def test_vertical_slice_exports_facts_and_proofs(self):
        repository = COKBRepository.load(SAMPLE)
        self.assertTrue(repository.validate().conforms)
        repository.infer()
        self.assertEqual(len(repository.assessments), 5)
        results = repository.find_mappings("k05.1")
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["assessment"]["level"], "A")

        with tempfile.TemporaryDirectory() as directory:
            repository.save(directory)
            output = Path(directory)
            expected = {
                "store.json",
                "validation_report.json",
                "proofs.json",
                "asserted_graph.ttl",
                "inferred_graph.ttl",
                "proof_graph.ttl",
            }
            self.assertEqual({item.name for item in output.iterdir()}, expected)
            report = json.loads((output / "validation_report.json").read_text())
            self.assertTrue(report["conforms"])

    def test_explanation_contains_rule_and_source(self):
        repository = COKBRepository.load(SAMPLE)
        repository.infer()
        explanation = repository.explain("mapping-k25-9-da60-y")
        proof = explanation["assessment"]["proof"]
        self.assertEqual(proof["rule_id"], "R-EXPLICIT-QUALIFIER-CONFLICT")
        self.assertEqual(proof["sources"], ["icd10cm_to_icd11_2024_full"])


if __name__ == "__main__":
    unittest.main()
