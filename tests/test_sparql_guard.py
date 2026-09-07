import unittest

from scripts.utils.sparql_guard import is_safe_construct_query


class SparqlGuardTests(unittest.TestCase):
    def test_accepts_construct(self):
        self.assertTrue(
            is_safe_construct_query(
                "PREFIX ex: <http://example.org/> CONSTRUCT { ?s ?p ?o } WHERE { ?s ?p ?o }"
            )
        )

    def test_rejects_update_and_service(self):
        self.assertFalse(is_safe_construct_query("INSERT DATA { <x> <y> <z> }"))
        self.assertFalse(
            is_safe_construct_query("CONSTRUCT { ?s ?p ?o } WHERE { SERVICE <https://x> { ?s ?p ?o } }")
        )

    def test_rejects_select_for_triple_parser(self):
        self.assertFalse(is_safe_construct_query("SELECT * WHERE { ?s ?p ?o }"))


if __name__ == "__main__":
    unittest.main()
