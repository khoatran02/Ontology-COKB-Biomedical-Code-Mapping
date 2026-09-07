from __future__ import annotations

import re


FORBIDDEN_KEYWORDS = {
    "ADD",
    "CLEAR",
    "COPY",
    "CREATE",
    "DELETE",
    "DROP",
    "INSERT",
    "LOAD",
    "MOVE",
    "SERVICE",
}


def is_safe_construct_query(query: str, max_characters: int = 20_000) -> bool:
    """Conservative guard for LLM-generated read-only retrieval queries."""
    if not isinstance(query, str) or not query.strip() or len(query) > max_characters:
        return False
    without_comments = re.sub(r"#[^\n]*", "", query)
    upper = without_comments.upper()
    syntax_only = re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|<[^>]*>', " ", upper)
    words = set(re.findall(r"\b[A-Z]+\b", syntax_only))
    if words & FORBIDDEN_KEYWORDS:
        return False
    operations = re.findall(r"\b(SELECT|CONSTRUCT|ASK|DESCRIBE)\b", syntax_only)
    return operations == ["CONSTRUCT"]
