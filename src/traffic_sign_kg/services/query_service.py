import re
from typing import Any

from traffic_sign_kg.repositories.fuseki_repository import FusekiRepository

_SAFE_URI = re.compile(r"^https?://[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=%-]+$")
PREFIXES = """
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX vko: <https://w3id.org/vn-ts-cokb/ontology#>
"""
GRAPH_SCOPE = """
FROM <https://w3id.org/vn-ts-cokb/graph/ontology>
FROM <https://w3id.org/vn-ts-cokb/graph/catalog>
FROM <https://w3id.org/vn-ts-cokb/graph/asserted>
FROM <https://w3id.org/vn-ts-cokb/graph/inferred/current>
"""


class UnsupportedQueryTemplateError(ValueError):
    pass


def _uri(value: str) -> str:
    if not _SAFE_URI.fullmatch(value) or ">" in value or "<" in value:
        raise ValueError(f"invalid absolute URI: {value}")
    return f"<{value}>"


class QueryService:
    def __init__(self, fuseki: FusekiRepository) -> None:
        self.fuseki = fuseki

    async def semantic_search(
        self,
        template_id: str,
        parameters: dict[str, str],
        limit: int,
    ) -> list[dict[str, Any]]:
        return await self.fuseki.select(self.compile_template(template_id, parameters, limit))

    @staticmethod
    def compile_template(template_id: str, parameters: dict[str, str], limit: int) -> str:
        if limit < 1 or limit > 500:
            raise ValueError("limit must be between 1 and 500")
        if template_id == "catalog_by_raw_code":
            raw_code = parameters.get("raw_code")
            if not raw_code or len(raw_code) > 64:
                raise ValueError("raw_code is required and must be at most 64 characters")
            escaped = raw_code.replace("\\", "\\\\").replace('"', '\\"')
            body = f'?entity vko:rawCode "{escaped}" .'
        elif template_id == "signs_by_maneuver":
            maneuver_uri = parameters.get("maneuver_uri")
            if maneuver_uri is None:
                raise ValueError("maneuver_uri is required")
            body = (
                "?entity vko:conveysRule ?rule . "
                f"?rule vko:prohibitsManeuver {_uri(maneuver_uri)} ."
            )
        elif template_id == "signs_by_family":
            family_uri = parameters.get("family_uri")
            if family_uri is None:
                raise ValueError("family_uri is required")
            body = f"?entity rdf:type/rdfs:subClassOf* {_uri(family_uri)} ."
        else:
            raise UnsupportedQueryTemplateError(f"unsupported template: {template_id}")
        return f"""
{PREFIXES}
SELECT DISTINCT ?entity ?type ?label
{GRAPH_SCOPE}
WHERE {{
  {body}
  OPTIONAL {{ ?entity rdf:type ?type . }}
  OPTIONAL {{ ?entity rdfs:label ?label . }}
}}
LIMIT {limit}
"""
