from __future__ import annotations

import csv
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from rdflib import OWL, RDF, RDFS, XSD, BNode, Graph, Literal, Namespace, URIRef

from traffic_sign_kg.cokb.facts import Fact, FactKind

VKO = Namespace("https://w3id.org/vn-ts-cokb/ontology#")
VKR = Namespace("https://w3id.org/vn-ts-cokb/resource/")
RULE = Namespace("https://w3id.org/vn-ts-cokb/resource/rule/")
CATALOG_ONTOLOGY = URIRef("https://w3id.org/vn-ts-cokb/catalog/vietnamese-signs")


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    class_id: int
    class_name: str
    raw_code: str
    base_code: str
    label_vi: str
    label_en: str
    family: str
    rule_id: str | None
    mapping_status: str

    @property
    def class_uri(self) -> URIRef:
        return VKO[self.class_name]

    @property
    def rule_uri(self) -> URIRef | None:
        return RULE[self.rule_id] if self.rule_id else None


# The catalog states only rules supported by the dataset labels. Missing semantics
# remain UNKNOWN/NeedsReview instead of being invented from visual appearance.
RULE_SEMANTICS: dict[str, dict[str, object]] = {
    "no-entry": {"kind": "ProhibitionRule", "prohibits": ("EnterRoad",)},
    "keep-right": {"kind": "ObligationRule", "requires": ("PassRight",)},
    "no-left-turn": {"kind": "ProhibitionRule", "prohibits": ("TurnLeft",)},
    "no-right-turn": {"kind": "ProhibitionRule", "prohibits": ("TurnRight",)},
    "no-u-turn": {"kind": "ProhibitionRule", "prohibits": ("UTurn",)},
    "no-car-u-turn": {
        "kind": "ProhibitionRule",
        "prohibits": ("UTurn",),
        "applies_to": ("PassengerCar",),
    },
    "no-right-turn-or-u-turn": {
        "kind": "ProhibitionRule",
        "prohibits": ("TurnRight", "UTurn"),
    },
    "no-left-or-right-turn": {
        "kind": "ProhibitionRule",
        "prohibits": ("TurnLeft", "TurnRight"),
    },
    "no-straight-or-right-turn": {
        "kind": "ProhibitionRule",
        "prohibits": ("GoStraight", "TurnRight"),
    },
    "no-left-turn-or-u-turn": {
        "kind": "ProhibitionRule",
        "prohibits": ("TurnLeft", "UTurn"),
    },
    "no-stopping-or-parking": {
        "kind": "ProhibitionRule",
        "prohibits": ("Stop", "Park"),
    },
    "no-parking": {"kind": "ProhibitionRule", "prohibits": ("Park",)},
    "left-turn-only": {"kind": "ObligationRule", "requires": ("TurnLeft",)},
    "no-truck": {"kind": "ProhibitionRule", "vehicles": ("Truck",)},
    "no-bus-or-truck": {
        "kind": "ProhibitionRule",
        "vehicles": ("Bus", "Truck"),
    },
    "no-car": {"kind": "ProhibitionRule", "vehicles": ("PassengerCar",)},
    "no-motorcycle": {"kind": "ProhibitionRule", "vehicles": ("Motorcycle",)},
    "no-semi-trailer": {"kind": "ProhibitionRule", "vehicles": ("SemiTrailer",)},
    "speed-40": {"kind": "ProhibitionRule", "value": Decimal("40")},
    "speed-50": {"kind": "ProhibitionRule", "value": Decimal("50")},
    "speed-60": {"kind": "ProhibitionRule", "value": Decimal("60")},
    "speed-80": {"kind": "ProhibitionRule", "value": Decimal("80")},
}


class SignCatalog:
    def __init__(self, entries: tuple[CatalogEntry, ...]) -> None:
        if len(entries) != 52:
            raise ValueError(f"catalog must contain 52 classes, found {len(entries)}")
        ids = [entry.class_id for entry in entries]
        codes = [entry.raw_code for entry in entries]
        names = [entry.class_name for entry in entries]
        if sorted(ids) != list(range(52)):
            raise ValueError("catalog class_id values must be exactly 0..51")
        if len(set(codes)) != len(codes) or len(set(names)) != len(names):
            raise ValueError("catalog raw_code and class_name values must be unique")
        unknown_rules = {
            entry.rule_id for entry in entries if entry.rule_id not in RULE_SEMANTICS
        } - {None}
        if unknown_rules:
            raise ValueError(f"catalog references unknown rules: {sorted(unknown_rules)}")
        self.entries = entries
        self._by_id = {entry.class_id: entry for entry in entries}
        self._by_uri = {str(entry.class_uri): entry for entry in entries}

    @classmethod
    def from_csv(cls, path: Path) -> SignCatalog:
        with path.open(encoding="utf-8", newline="") as stream:
            rows = csv.DictReader(stream)
            entries = tuple(
                CatalogEntry(
                    class_id=int(row["class_id"]),
                    class_name=row["class_name"],
                    raw_code=row["raw_code"],
                    base_code=row["base_code"],
                    label_vi=row["label_vi"],
                    label_en=row["label_en"],
                    family=row["family"],
                    rule_id=row["rule_id"] or None,
                    mapping_status=row["mapping_status"],
                )
                for row in rows
            )
        return cls(entries)

    def by_id(self, class_id: int) -> CatalogEntry:
        try:
            return self._by_id[class_id]
        except KeyError as exc:
            raise ValueError(f"unknown dataset class_id: {class_id}") from exc

    def by_uri(self, class_uri: str) -> CatalogEntry:
        try:
            return self._by_uri[class_uri]
        except KeyError as exc:
            raise ValueError(f"class URI is not present in the catalog: {class_uri}") from exc

    def to_graph(self) -> Graph:
        graph = Graph(identifier=URIRef("https://w3id.org/vn-ts-cokb/graph/catalog"))
        graph.bind("vko", VKO)
        graph.bind("vkr", VKR)
        graph.bind("rule", RULE)
        graph.add((CATALOG_ONTOLOGY, RDF.type, OWL.Ontology))
        graph.add((CATALOG_ONTOLOGY, OWL.imports, URIRef("https://w3id.org/vn-ts-cokb/ontology")))
        graph.add((CATALOG_ONTOLOGY, OWL.versionInfo, Literal("1.0.0")))
        for entry in self.entries:
            self._add_entry(graph, entry)
        for rule_id, semantics in RULE_SEMANTICS.items():
            self._add_rule(graph, rule_id, semantics)
        return graph

    def static_facts(self) -> tuple[Fact, ...]:
        facts: list[Fact] = []
        for entry in self.entries:
            facts.append(
                Fact(
                    "subClassOf",
                    (str(entry.class_uri), str(VKO[entry.family])),
                    FactKind.TYPE,
                    source="catalog-1.0.0",
                )
            )
            if entry.rule_uri:
                facts.append(
                    Fact(
                        "classConveysRule",
                        (str(entry.class_uri), str(entry.rule_uri)),
                        source="catalog-1.0.0",
                    )
                )
        for child, parent in (
            ("PassengerCar", "MotorVehicle"),
            ("Truck", "MotorVehicle"),
            ("Bus", "MotorVehicle"),
            ("Motorcycle", "MotorVehicle"),
            ("SemiTrailer", "MotorVehicle"),
            ("MotorVehicle", "Vehicle"),
        ):
            facts.append(
                Fact(
                    "broaderVehicleCategory",
                    (str(VKO[child]), str(VKO[parent])),
                    FactKind.TYPE,
                    source="ontology-1.0.0",
                )
            )
        for rule_id, semantics in RULE_SEMANTICS.items():
            rule_uri = str(RULE[rule_id])
            for maneuver in semantics.get("prohibits", ()):
                facts.append(
                    Fact(
                        "prohibitsManeuver",
                        (rule_uri, str(VKO[str(maneuver)])),
                        source="catalog-1.0.0",
                    )
                )
            for maneuver in semantics.get("requires", ()):
                facts.append(
                    Fact(
                        "requiresManeuver",
                        (rule_uri, str(VKO[str(maneuver)])),
                        source="catalog-1.0.0",
                    )
                )
            applies_to = semantics.get("applies_to") or semantics.get("vehicles") or ("Vehicle",)
            for vehicle in applies_to:
                facts.append(
                    Fact(
                        "appliesTo",
                        (rule_uri, str(VKO[str(vehicle)])),
                        source="catalog-1.0.0",
                    )
                )
            for vehicle in semantics.get("vehicles", ()):
                facts.append(
                    Fact(
                        "prohibitsVehicleCategory",
                        (rule_uri, str(VKO[str(vehicle)])),
                        source="catalog-1.0.0",
                    )
                )
            if "value" in semantics:
                facts.append(
                    Fact(
                        "restrictionValue",
                        (rule_uri, semantics["value"], str(VKO.KilometrePerHour)),
                        FactKind.FUNCTION_VALUE,
                        source="catalog-1.0.0",
                    )
                )
        return tuple(facts)

    @staticmethod
    def _add_entry(graph: Graph, entry: CatalogEntry) -> None:
        graph.add((entry.class_uri, RDF.type, OWL.Class))
        graph.add((entry.class_uri, RDFS.subClassOf, VKO[entry.family]))
        graph.add((entry.class_uri, VKO.sourceClassId, Literal(entry.class_id)))
        graph.add((entry.class_uri, VKO.rawCode, Literal(entry.raw_code)))
        graph.add((entry.class_uri, VKO.baseCode, Literal(entry.base_code)))
        graph.add((entry.class_uri, RDFS.label, Literal(entry.label_vi, lang="vi")))
        graph.add((entry.class_uri, RDFS.label, Literal(entry.label_en, lang="en")))
        graph.add((entry.class_uri, VKO.mappingStatus, VKO[entry.mapping_status]))
        if entry.rule_uri:
            graph.add((entry.class_uri, VKO.canonicalRule, entry.rule_uri))
            restriction = BNode()
            graph.add((entry.class_uri, RDFS.subClassOf, restriction))
            graph.add((restriction, RDF.type, OWL.Restriction))
            graph.add((restriction, OWL.onProperty, VKO.conveysRule))
            graph.add((restriction, OWL.hasValue, entry.rule_uri))

    @staticmethod
    def _add_rule(graph: Graph, rule_id: str, semantics: dict[str, object]) -> None:
        rule_uri = RULE[rule_id]
        graph.add((rule_uri, RDF.type, VKO[str(semantics["kind"])]))
        applies_to = semantics.get("applies_to") or semantics.get("vehicles") or ("Vehicle",)
        for vehicle in applies_to:
            graph.add((rule_uri, VKO.appliesTo, VKO[str(vehicle)]))
        for maneuver in semantics.get("prohibits", ()):
            graph.add((rule_uri, VKO.prohibitsManeuver, VKO[str(maneuver)]))
        for maneuver in semantics.get("requires", ()):
            graph.add((rule_uri, VKO.requiresManeuver, VKO[str(maneuver)]))
        for vehicle in semantics.get("vehicles", ()):
            graph.add((rule_uri, VKO.prohibitsVehicleCategory, VKO[str(vehicle)]))
        if "value" in semantics:
            graph.add(
                (
                    rule_uri,
                    VKO.hasRestrictionValue,
                    Literal(semantics["value"], datatype=XSD.decimal),
                )
            )
            graph.add((rule_uri, VKO.hasUnit, VKO.KilometrePerHour))
