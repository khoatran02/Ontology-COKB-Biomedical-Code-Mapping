import re
from typing import Any

from traffic_sign_kg.domain.models import VectorCandidate
from traffic_sign_kg.repositories.faiss_repository import FaissVectorRepository
from traffic_sign_kg.repositories.fuseki_repository import FusekiRepository

_SAFE_URI = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")
PREFIXES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX vko: <https://example.org/traffic-sign-kg/ontology#>
"""


class UnsupportedQueryTemplateError(ValueError):
    pass


def _uri(value: str) -> str:
    if not _SAFE_URI.fullmatch(value) or ">" in value or "<" in value:
        raise ValueError(f"invalid absolute URI: {value}")
    return f"<{value}>"


class QueryService:
    def __init__(
        self,
        vectors: FaissVectorRepository,
        fuseki: FusekiRepository,
    ) -> None:
        self.vectors = vectors
        self.fuseki = fuseki

    def vector_search(
        self,
        index_name: str,
        vector: list[float],
        candidate_limit: int,
    ) -> list[VectorCandidate]:
        return self.vectors.search(index_name, vector, candidate_limit)

    async def semantic_search(
        self,
        template_id: str,
        parameters: dict[str, str],
        limit: int,
    ) -> list[dict[str, Any]]:
        query = self._compile_template(template_id, parameters, limit)
        return await self.fuseki.select(query)

    async def hybrid_filter(
        self,
        candidates: list[VectorCandidate],
        *,
        sign_family_uri: str | None = None,
        applies_to_uri: str | None = None,
        result_limit: int = 20,
    ) -> list[VectorCandidate]:
        if not candidates:
            return []
        values = " ".join(_uri(candidate.rdf_uri) for candidate in candidates)
        constraints: list[str] = []
        if sign_family_uri:
            constraints.append(f"?type rdfs:subClassOf* {_uri(sign_family_uri)} .")
        if applies_to_uri:
            constraints.append(f"?rule vko:appliesTo/rdfs:subClassOf* {_uri(applies_to_uri)} .")
        query = f"""
{PREFIXES}
SELECT DISTINCT ?sign
WHERE {{
  VALUES ?sign {{ {values} }}
  ?sign rdf:type ?type .
  OPTIONAL {{ ?sign vko:conveysRule ?rule . }}
  {" ".join(constraints)}
}}
"""
        rows = await self.fuseki.select(query)
        accepted = {
            binding["sign"]["value"]
            for binding in rows
            if "sign" in binding and "value" in binding["sign"]
        }
        return [candidate for candidate in candidates if candidate.rdf_uri in accepted][
            :result_limit
        ]

    @staticmethod
    def _compile_template(
        template_id: str,
        parameters: dict[str, str],
        limit: int,
    ) -> str:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if template_id == "find_by_raw_code":
            raw_code = parameters.get("raw_code")
            if not raw_code or len(raw_code) > 64:
                raise ValueError("raw_code is required and must be at most 64 characters")
            escaped = raw_code.replace("\\", "\\\\").replace('"', '\\"')
            body = f'?sign vko:rawCode "{escaped}" .'
        elif template_id == "find_by_sign_family":
            family_uri = parameters.get("sign_family_uri")
            if family_uri is None:
                raise ValueError("sign_family_uri is required")
            body = f"?sign rdf:type/rdfs:subClassOf* {_uri(family_uri)} ."
        elif template_id == "find_by_maneuver":
            maneuver_uri = parameters.get("maneuver_uri")
            if maneuver_uri is None:
                raise ValueError("maneuver_uri is required")
            body = (
                f"?sign vko:conveysRule ?rule . ?rule vko:prohibitsManeuver {_uri(maneuver_uri)} ."
            )
        else:
            raise UnsupportedQueryTemplateError(f"unsupported template: {template_id}")
        return f"""
{PREFIXES}
SELECT DISTINCT ?sign ?type ?label
WHERE {{
  {body}
  ?sign rdf:type ?type .
  OPTIONAL {{ ?sign rdfs:label ?label . }}
}}
LIMIT {limit}
"""
