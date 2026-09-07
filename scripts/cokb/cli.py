from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.cokb.repository import COKBRepository


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SAMPLE = REPO_ROOT / "examples" / "icd_mapping_sample.json"


def add_cokb_subcommands(subparsers: argparse._SubParsersAction) -> None:
    build = subparsers.add_parser("cokb_build", help="Build asserted, inferred, and proof COKB artifacts")
    build.add_argument("--input", default=str(DEFAULT_SAMPLE), help="Mapping JSON input")
    build.add_argument("--output", default="./graph_data/cokb", help="Output directory")

    graph_import = subparsers.add_parser(
        "cokb_import_graph", help="Import the existing Oxigraph mapping graph into the COKB contract"
    )
    graph_import.add_argument("--graph-store", required=True)
    graph_import.add_argument("--source-system", default="ICD10CM")
    graph_import.add_argument("--target-system", default="ICD11")
    graph_import.add_argument("--evidence-source", default="icd10cm_to_icd11_2024_full")
    graph_import.add_argument("--output", default="./graph_data/cokb")

    validate = subparsers.add_parser("cokb_validate", help="Validate mapping assertions")
    validate.add_argument("--input", default=str(DEFAULT_SAMPLE), help="Mapping JSON or COKB store")

    shacl = subparsers.add_parser("cokb_shacl", help="Run optional standards-based SHACL validation")
    shacl.add_argument("--store", default="./graph_data/cokb", help="Built COKB artifact directory")
    shacl.add_argument("--report", default="./graph_data/cokb/shacl_report.ttl")

    reason = subparsers.add_parser("cokb_reason", help="Run deterministic COKB rules")
    reason.add_argument("--input", default=str(DEFAULT_SAMPLE), help="Mapping JSON or COKB store")
    reason.add_argument("--output", default="./graph_data/cokb", help="Output directory")

    query = subparsers.add_parser("cokb_query", help="Find mappings and their proofs")
    query.add_argument("--store", default="./graph_data/cokb", help="COKB store directory or JSON")
    query.add_argument("--code", required=True, help="Source code")
    query.add_argument("--system", help="Optional source code system")

    explain = subparsers.add_parser("cokb_explain", help="Explain one mapping assertion")
    explain.add_argument("--store", default="./graph_data/cokb", help="COKB store directory or JSON")
    explain.add_argument("--mapping-id", required=True)

    demo = subparsers.add_parser("cokb_demo", help="Run the offline COKB vertical slice")
    demo.add_argument("--output", default="./graph_data/cokb_demo")
    demo.add_argument("--code", default="K05.1")

    evaluation = subparsers.add_parser("cokb_eval", help="Evaluate deterministic rules on mapping-level gold data")
    evaluation.add_argument(
        "--gold",
        default="./gold_datasets/mapping_level/code_pair_mapping_level__gold_standard__reasoning.xlsx",
    )
    evaluation.add_argument("--output", help="Optional JSON report path")


def _print(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _write_quarantine(repository: COKBRepository, report, output_directory: str | Path) -> None:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    invalid_ids = {
        issue.mapping_id
        for issue in report.issues
        if issue.severity == "error" and issue.mapping_id is not None
    }
    quarantined = [
        mapping.to_dict() for mapping in repository.mappings if mapping.mapping_id in invalid_ids
    ]
    (output / "validation_report.json").write_text(
        json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (output / "quarantine.json").write_text(
        json.dumps({"mappings": quarantined}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def run_cokb_command(args: argparse.Namespace) -> int:
    if args.task == "cokb_import_graph":
        from scripts.cokb.importer import import_oxigraph_store

        try:
            repository = import_oxigraph_store(
                graph_store=args.graph_store,
                source_system=args.source_system,
                target_system=args.target_system,
                evidence_source=args.evidence_source,
            )
        except (RuntimeError, OSError, ValueError) as error:
            _print({"error": str(error)})
            return 3
        report = repository.validate()
        if not report.conforms:
            _write_quarantine(repository, report, args.output)
            _print(report.to_dict())
            return 1
        repository.infer()
        repository.save(args.output)
        _print(
            {
                "status": "ok",
                "mapping_count": len(repository.mappings),
                "assessment_count": len(repository.assessments),
                "output": str(Path(args.output).resolve()),
            }
        )
        return 0

    if args.task in {"cokb_build", "cokb_reason"}:
        repository = COKBRepository.load(args.input)
        report = repository.validate()
        if not report.conforms:
            _write_quarantine(repository, report, args.output)
            _print(report.to_dict())
            return 1
        repository.infer()
        repository.save(args.output)
        _print(
            {
                "status": "ok",
                "mapping_count": len(repository.mappings),
                "assessment_count": len(repository.assessments),
                "output": str(Path(args.output).resolve()),
            }
        )
        return 0

    if args.task == "cokb_validate":
        report = COKBRepository.load(args.input).validate()
        _print(report.to_dict())
        return 0 if report.conforms else 1

    if args.task == "cokb_shacl":
        from scripts.cokb.shacl import validate_shacl

        store = Path(args.store)
        try:
            conforms, report_graph, report_text = validate_shacl(
                data_paths=(
                    store / "asserted_graph.ttl",
                    store / "inferred_graph.ttl",
                    store / "proof_graph.ttl",
                ),
                ontology_path=REPO_ROOT / "ontology" / "biomedical_mapping_cokb.ttl",
                shapes_path=REPO_ROOT / "shapes" / "biomedical_mapping_shapes.ttl",
            )
        except (RuntimeError, OSError, ValueError) as error:
            _print({"conforms": False, "error": str(error)})
            return 3
        report_path = Path(args.report)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report_graph, encoding="utf-8")
        _print({"conforms": conforms, "report": str(report_path.resolve()), "details": report_text})
        return 0 if conforms else 1

    if args.task == "cokb_query":
        repository = COKBRepository.load(args.store)
        if not repository.assessments:
            repository.infer()
        results = repository.find_mappings(args.code, args.system)
        _print({"source_code": args.code, "count": len(results), "mappings": results})
        return 0 if results else 2

    if args.task == "cokb_explain":
        repository = COKBRepository.load(args.store)
        if not repository.assessments:
            repository.infer()
        try:
            _print(repository.explain(args.mapping_id))
        except KeyError as error:
            _print({"error": str(error)})
            return 2
        return 0

    if args.task == "cokb_demo":
        repository = COKBRepository.load(DEFAULT_SAMPLE)
        report = repository.validate()
        if not report.conforms:
            _print(report.to_dict())
            return 1
        repository.infer()
        repository.save(args.output)
        _print(
            {
                "status": "ok",
                "query": args.code,
                "mappings": repository.find_mappings(args.code),
                "artifacts": str(Path(args.output).resolve()),
            }
        )
        return 0

    if args.task == "cokb_eval":
        from scripts.cokb.evaluation import evaluate_mapping_level_xlsx

        try:
            result = evaluate_mapping_level_xlsx(args.gold)
        except (RuntimeError, OSError, ValueError, KeyError, SyntaxError) as error:
            _print({"error": str(error)})
            return 3
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        summary = {key: value for key, value in result.items() if key != "predictions"}
        _print(summary)
        return 0

    raise ValueError(f"Unsupported COKB task: {args.task}")
