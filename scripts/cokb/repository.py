from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from scripts.cokb.model import MappingAssessment, MappingAssertion, ValidationReport
from scripts.cokb.operators import normalize_code
from scripts.cokb.reasoner import COKBReasoner
from scripts.cokb.validation import validate_mappings


SCHEMA_VERSION = "1.0"
BASE_IRI = "http://iqvia.com/ontologies/cokb/"


def _slug(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._~-]+", "-", value).strip("-")
    return cleaned or "unknown"


def _literal(value: Any) -> str:
    return json.dumps(str(value), ensure_ascii=False)


@dataclass
class COKBRepository:
    mappings: list[MappingAssertion] = field(default_factory=list)
    assessments: list[MappingAssessment] = field(default_factory=list)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "COKBRepository":
        mappings = [MappingAssertion.from_dict(item) for item in payload.get("mappings", [])]
        return cls(mappings=mappings)

    @classmethod
    def load(cls, path: str | Path) -> "COKBRepository":
        source = Path(path)
        if source.is_dir():
            source = source / "store.json"
        payload = json.loads(source.read_text(encoding="utf-8"))
        repository = cls.from_dict(payload)
        if payload.get("assessments"):
            # Stored assessments are recomputed to preserve deterministic rule semantics.
            repository.infer()
        return repository

    def validate(self) -> ValidationReport:
        return validate_mappings(self.mappings)

    def infer(self, reasoner: COKBReasoner | None = None) -> list[MappingAssessment]:
        engine = reasoner or COKBReasoner()
        self.assessments = engine.assess_all(self.mappings)
        return self.assessments

    def find_mappings(self, source_code: str, source_system: str | None = None) -> list[dict[str, Any]]:
        code = normalize_code(source_code)
        assessment_by_id = {item.mapping_id: item for item in self.assessments}
        results: list[dict[str, Any]] = []
        for mapping in self.mappings:
            if normalize_code(mapping.source.code) != code:
                continue
            if source_system and mapping.source.system.casefold() != source_system.casefold():
                continue
            item = mapping.to_dict()
            assessment = assessment_by_id.get(mapping.mapping_id)
            item["assessment"] = assessment.to_dict() if assessment else None
            results.append(item)
        return results

    def explain(self, mapping_id: str) -> dict[str, Any]:
        mapping = next((item for item in self.mappings if item.mapping_id == mapping_id), None)
        if mapping is None:
            raise KeyError(f"Unknown mapping_id: {mapping_id}")
        assessment = next((item for item in self.assessments if item.mapping_id == mapping_id), None)
        if assessment is None:
            assessment = COKBReasoner().assess(mapping)
        return {"mapping": mapping.to_dict(), "assessment": assessment.to_dict()}

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "mappings": [mapping.to_dict() for mapping in self.mappings],
            "assessments": [assessment.to_dict() for assessment in self.assessments],
        }

    def save(self, output_directory: str | Path) -> None:
        output = Path(output_directory)
        output.mkdir(parents=True, exist_ok=True)
        (output / "store.json").write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (output / "validation_report.json").write_text(
            json.dumps(self.validate().to_dict(), indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        (output / "proofs.json").write_text(
            json.dumps(
                [assessment.proof.to_dict() for assessment in self.assessments],
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        (output / "asserted_graph.ttl").write_text(self.asserted_turtle(), encoding="utf-8")
        (output / "inferred_graph.ttl").write_text(self.inferred_turtle(), encoding="utf-8")
        (output / "proof_graph.ttl").write_text(self.proof_turtle(), encoding="utf-8")

    def asserted_turtle(self) -> str:
        lines = [
            "@prefix cokb: <http://iqvia.com/ontologies/cokb/> .",
            "@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .",
            "@prefix prov: <http://www.w3.org/ns/prov#> .",
            "",
        ]
        emitted: set[str] = set()
        emitted_evidence: set[str] = set()
        for mapping in self.mappings:
            source_iri = f"cokb:concept-{_slug(mapping.source.system)}-{_slug(mapping.source.code)}"
            target_iri = f"cokb:concept-{_slug(mapping.target.system)}-{_slug(mapping.target.code)}"
            mapping_iri = f"cokb:{_slug(mapping.mapping_id)}"
            evidence_iri = f"cokb:evidence-{_slug(mapping.evidence_source)}"
            if evidence_iri not in emitted_evidence:
                emitted_evidence.add(evidence_iri)
                lines.extend(
                    [
                        f"{evidence_iri} a cokb:EvidenceSource ;",
                        f"    rdfs:label {_literal(mapping.evidence_source)} .",
                        "",
                    ]
                )
            for iri, concept in ((source_iri, mapping.source), (target_iri, mapping.target)):
                if iri in emitted:
                    continue
                emitted.add(iri)
                lines.extend(
                    [
                        f"{iri} a cokb:CodeConcept ;",
                        f"    cokb:codeSystem {_literal(concept.system)} ;",
                        f"    cokb:mappedValue {_literal(concept.code)} ;",
                        f"    rdfs:label {_literal(concept.label)} .",
                        "",
                    ]
                )
            lines.extend(
                [
                    f"{mapping_iri} a cokb:MappingAssertion ;",
                    f"    cokb:mapsFrom {source_iri} ;",
                    f"    cokb:mapsTo {target_iri} ;",
                    f"    prov:wasDerivedFrom {evidence_iri} ;",
                    f"    cokb:supportedBy {evidence_iri} ;",
                    f"    cokb:assertedBy {_literal(mapping.asserted_by)} .",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def inferred_turtle(self) -> str:
        lines = ["@prefix cokb: <http://iqvia.com/ontologies/cokb/> .", ""]
        for assessment in self.assessments:
            assessment_iri = f"cokb:assessment-{_slug(assessment.mapping_id)}"
            lines.extend(
                [
                    f"{assessment_iri} a cokb:RuleBasedAssessment ;",
                    f"    cokb:assessesMapping cokb:{_slug(assessment.mapping_id)} ;",
                    f"    cokb:hasMappingLevel cokb:Level-{assessment.level.value} ;",
                    f"    cokb:producedByRule cokb:{_slug(assessment.proof.rule_id)} .",
                    "",
                ]
            )
        return "\n".join(lines).rstrip() + "\n"

    def proof_turtle(self) -> str:
        lines = [
            "@prefix cokb: <http://iqvia.com/ontologies/cokb/> .",
            "@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .",
            "",
        ]
        for assessment in self.assessments:
            proof_iri = f"cokb:proof-{_slug(assessment.mapping_id)}"
            premise_iris = [
                f"cokb:premise-{_slug(assessment.mapping_id)}-{index}"
                for index, _ in enumerate(assessment.proof.premises, start=1)
            ]
            source_iris = [f"cokb:evidence-{_slug(source)}" for source in assessment.proof.sources]
            proof_lines = [
                f"{proof_iri} a cokb:ProofTrace ;",
                f"    cokb:provesAssessment cokb:assessment-{_slug(assessment.mapping_id)} ;",
                f"    cokb:producedByRule cokb:{_slug(assessment.proof.rule_id)} ;",
                f"    cokb:hasPremiseCount {len(assessment.proof.premises)}",
            ]
            for iri in premise_iris:
                proof_lines[-1] += " ;"
                proof_lines.append(f"    cokb:hasPremise {iri}")
            for iri in source_iris:
                proof_lines[-1] += " ;"
                proof_lines.append(f"    cokb:supportedBy {iri}")
            proof_lines[-1] += " ."
            lines.extend(proof_lines + [""])
            for premise_iri, premise in zip(premise_iris, assessment.proof.premises):
                value = (
                    json.dumps(premise.value, ensure_ascii=False, sort_keys=True)
                    if isinstance(premise.value, (dict, list, tuple))
                    else str(premise.value).lower()
                    if isinstance(premise.value, bool)
                    else str(premise.value)
                )
                lines.extend(
                    [
                        f"{premise_iri} a cokb:Premise ;",
                        f"    cokb:premisePredicate {_literal(premise.predicate)} ;",
                        f"    cokb:premiseValue {_literal(value)} ;",
                        f"    cokb:premiseSource {_literal(premise.source)} .",
                        "",
                    ]
                )
        return "\n".join(lines).rstrip() + "\n"
