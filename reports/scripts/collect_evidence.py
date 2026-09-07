"""Reproduce report evidence without modifying the original graph or gold data."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.dont_write_bytecode = True

from scripts.cokb.evaluation import evaluate_mapping_level_xlsx
from scripts.cokb.repository import COKBRepository
from scripts.cokb.xlsx import read_first_sheet_records


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    output = ROOT / "reports/artifacts"
    output.mkdir(parents=True, exist_ok=True)
    gold = ROOT / "gold_datasets/mapping_level/code_pair_mapping_level__gold_standard__reasoning.xlsx"
    sample = ROOT / "examples/icd_mapping_sample.json"
    evaluation = evaluate_mapping_level_xlsx(str(gold))
    write_json(output / "evaluation.json", evaluation)
    repository = COKBRepository.load(sample)
    validation = repository.validate()
    if not validation.conforms:
        raise RuntimeError("Sample validation failed")
    repository.infer()
    repository.save(output / "demo")
    write_json(output / "query_k05_1.json", repository.find_mappings("K05.1", "ICD10WHO"))
    write_json(output / "explain_exact.json", repository.explain("mapping-k05-1-da0b-y"))
    test_run = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT, text=True, capture_output=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    (output / "unit_tests.txt").write_text(test_run.stdout + test_run.stderr, encoding="utf-8")
    inputs = sorted((ROOT / "scripts/cokb").glob("*.py"))
    inputs += sorted((ROOT / "tests").glob("*.py"))
    inputs += [
        gold, sample, ROOT / "ontology/biomedical_mapping_cokb.ttl",
        ROOT / "shapes/biomedical_mapping_shapes.ttl",
        ROOT / "rules/mapping_rules.json", ROOT / "scripts/utils/indexer.py",
        ROOT / "scripts/utils/sparql_guard.py", ROOT / "main.py", ROOT / "pyproject.toml",
    ]
    graph_state: dict[str, object]
    try:
        from pyoxigraph import Store
        from scripts.cokb.importer import MAPPING_QUERY
        store = Store.read_only(str(ROOT / "graph_data/graph_store"))
        graph_state = {"quad_count": len(store), "mapping_rows": len(list(store.query(MAPPING_QUERY)))}
        del store
    except (ImportError, OSError, RuntimeError) as error:
        graph_state = {"not_verified": str(error)}
    source_ttl = ROOT / "graph_data/source_ttl/icd10cm_to_icd11_2024_full.ttl"
    with source_ttl.open("rb") as handle:
        prefix = handle.read(1024)
    is_pointer = prefix.startswith(b"version https://git-lfs.github.com/spec/v1")
    records = read_first_sheet_records(str(gold))
    incorrect = [
        {"row_index_zero_based": i, "record": records[i], "prediction": prediction}
        for i, prediction in enumerate(evaluation["predictions"])
        if prediction["predicted"] != "UNASSESSED" and prediction["predicted"] != prediction["gold"]
    ]
    summary = {
        "collected_at": datetime.now(timezone(timedelta(hours=7))).isoformat(),
        "python": platform.python_version(),
        "metrics": {k: v for k, v in evaluation.items() if k != "predictions"},
        "selected_rules": dict(Counter(p["rule_id"] for p in evaluation["predictions"])),
        "assessed_errors": incorrect,
        "sample_validation": validation.to_dict(),
        "sample_results": [
            {"mapping_id": a.mapping_id, "level": a.level.value, "rule_id": a.proof.rule_id}
            for a in repository.assessments
        ],
        "unit_tests_exit_code": test_run.returncode,
        "unit_tests_log": "unit_tests.txt",
        "graph_store_read_only": graph_state,
        "source_ttl_is_lfs_pointer": is_pointer,
        "lfs_pointer": prefix.decode("utf-8") if is_pointer else None,
        "sha256": {str(p.relative_to(ROOT)): sha256(p.read_bytes()).hexdigest() for p in inputs},
    }
    write_json(output / "summary.json", summary)
    print(json.dumps({
        "output": str(output),
        "total": evaluation["total"],
        "coverage": evaluation["coverage"],
        "unit_tests_exit_code": test_run.returncode,
        "graph_store": graph_state,
    }, indent=2))
    return test_run.returncode


if __name__ == "__main__":
    raise SystemExit(main())
