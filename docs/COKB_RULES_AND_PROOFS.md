# COKB Rules and Proof Traces

## Ordered rule policy

Rules are evaluated in this order:

1. `R-EXACT-LABEL`: normalised labels are equal → level A.
2. `R-EXPLICIT-QUALIFIER-CONFLICT`: explicit qualifiers conflict → level C.
3. `R-COMPATIBLE-SPECIFICITY`: one label is a non-conflicting specialization → level B.
4. `R-GENERALIZED-CONDITION`: labels share a condition and one is explicitly generalized → level B.
5. `R-INSUFFICIENT-EVIDENCE`: no rule has enough evidence → `UNASSESSED`.

The fallback is deliberately not level C. Unrelated-looking labels are not automatically proven to conflict.

## Proof contract

Every rule-based assessment contains:

```json
{
  "conclusion": {
    "mapping_id": "mapping-k05-1-da0b-y",
    "predicate": "hasMappingLevel",
    "object": "A"
  },
  "premises": [
    {
      "predicate": "normalizedSourceLabel",
      "value": "chronic gingivitis",
      "source": "icd10cm_to_icd11_2024_full"
    }
  ],
  "rule_id": "R-EXACT-LABEL",
  "sources": ["icd10cm_to_icd11_2024_full"]
}
```

This is an externally inspectable proof record, not hidden chain-of-thought.

## Limitations

The initial deterministic rules cover high-confidence lexical cases. They do not prove arbitrary clinical equivalence. Semantic cases beyond the rule set remain `UNASSESSED` and may receive a separate human or model assessment. Extending the rules requires a rule identifier, tests, a documented evidence policy, and evaluation against the existing gold dataset.

## Evaluation interpretation

`cokb_eval` reports both rule coverage and accuracy. A conservative reasoner may have high accuracy on assessed mappings while leaving many cases `UNASSESSED`; both values must be reported. This avoids hiding abstentions inside an aggregate score.
