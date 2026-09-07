# COKB Evaluation

## Protocol

The deterministic reasoner is evaluated against the repository's 500-row mapping-level gold dataset. The evaluator reads XLSX using the Python standard library, so COKB evaluation does not require pandas.

```shell
python3 main.py cokb_eval
```

Metrics distinguish:

- **coverage**: fraction receiving A, B, or C instead of `UNASSESSED`;
- **overall accuracy**: correct predictions divided by all rows;
- **accuracy when assessed**: correct predictions divided by covered rows;
- per-level precision, recall, and F1.

## Initial deterministic baseline

For the committed high-confidence rules:

| Metric | Result |
|---|---:|
| Rows | 500 |
| Coverage | 4.40% |
| Overall accuracy | 4.20% |
| Accuracy when assessed | 95.45% |
| Unassessed | 478 |

This is intentionally conservative. It demonstrates that explicit rules and proofs work, but it is not a replacement for clinical semantic review. Reporting only the 95.45% assessed accuracy would be misleading because rule coverage is low.

## Extension policy

New rules should improve coverage without hiding uncertainty. Every added rule requires:

1. a stable rule identifier;
2. a documented condition and conclusion;
3. positive and negative unit tests;
4. a proof-premise policy;
5. before/after coverage and per-level metrics.

The existing LLM experiment results remain a separate baseline. A future hybrid evaluation should compare rule-based, model-based, and human assessments without promoting model predictions to asserted COKB facts.
