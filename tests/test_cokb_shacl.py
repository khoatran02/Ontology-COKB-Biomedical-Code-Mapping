import importlib.util
import tempfile
import unittest
from pathlib import Path

from scripts.cokb.repository import COKBRepository
from scripts.cokb.shacl import validate_shacl


ROOT = Path(__file__).resolve().parents[1]
HAS_SHACL = importlib.util.find_spec("pyshacl") is not None and importlib.util.find_spec("rdflib") is not None


@unittest.skipUnless(HAS_SHACL, "optional SHACL dependencies are not installed")
class ShaclTests(unittest.TestCase):
    def test_generated_graphs_conform(self):
        repository = COKBRepository.load(ROOT / "examples" / "icd_mapping_sample.json")
        repository.infer()
        with tempfile.TemporaryDirectory() as directory:
            repository.save(directory)
            output = Path(directory)
            conforms, _, _ = validate_shacl(
                (
                    output / "asserted_graph.ttl",
                    output / "inferred_graph.ttl",
                    output / "proof_graph.ttl",
                ),
                ROOT / "ontology" / "biomedical_mapping_cokb.ttl",
                ROOT / "shapes" / "biomedical_mapping_shapes.ttl",
            )
            self.assertTrue(conforms)


if __name__ == "__main__":
    unittest.main()
