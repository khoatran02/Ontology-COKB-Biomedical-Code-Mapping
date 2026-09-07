from __future__ import annotations

import re
import unicodedata


_PHRASE_ALIASES = {
    "haemorrhage": "hemorrhage",
    "haemorrhagic": "hemorrhagic",
    "renal": "kidney",
}

_STOPWORDS = {
    "a",
    "an",
    "and",
    "due",
    "of",
    "or",
    "the",
    "to",
}

_CONFLICT_PAIRS = (
    ("acute", "chronic"),
    ("benign", "malignant"),
    ("left", "right"),
    ("type 1", "type 2"),
    ("with hemorrhage", "without hemorrhage"),
    ("hemorrhagic", "without hemorrhage"),
    ("with perforation", "without perforation"),
)


def normalize_code(code: str) -> str:
    """Normalize presentation while retaining clinically meaningful punctuation."""
    return re.sub(r"\s+", "", str(code)).upper()


def normalize_label(label: str) -> str:
    text = unicodedata.normalize("NFKC", str(label)).casefold()
    text = re.sub(r"[_/(),;:-]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    tokens = [_PHRASE_ALIASES.get(token, token) for token in text.split()]
    return " ".join(tokens)


def content_tokens(label: str) -> set[str]:
    return {token for token in normalize_label(label).split() if token not in _STOPWORDS}


def find_explicit_conflicts(source_label: str, target_label: str) -> list[str]:
    source = normalize_label(source_label)
    target = normalize_label(target_label)
    conflicts: list[str] = []
    for left, right in _CONFLICT_PAIRS:
        if (left in source and right in target) or (right in source and left in target):
            conflicts.append(f"{left} <> {right}")
    return conflicts


def labels_are_equivalent(source_label: str, target_label: str) -> bool:
    return normalize_label(source_label) == normalize_label(target_label)


def labels_have_compatible_specificity(source_label: str, target_label: str) -> bool:
    if find_explicit_conflicts(source_label, target_label):
        return False
    source_tokens = content_tokens(source_label)
    target_tokens = content_tokens(target_label)
    return bool(source_tokens and target_tokens) and (
        source_tokens < target_tokens or target_tokens < source_tokens
    )


def labels_share_generalized_condition(source_label: str, target_label: str) -> bool:
    if find_explicit_conflicts(source_label, target_label):
        return False
    source = content_tokens(source_label)
    target = content_tokens(target_label)
    shared = source & target
    generalized = {"unspecified", "other"}
    return bool(shared) and bool((source | target) & generalized)
