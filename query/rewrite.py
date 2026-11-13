from __future__ import annotations

from collections.abc import Mapping, Sequence
import re

_REGULATORY_EXPANSIONS = {
    "ppi": "Prepaid Payment Instruments",
    "kyc": "Know Your Customer",
    "aml": "Anti Money Laundering",
    "pmla": "Prevention of Money Laundering Act",
    "upi": "Unified Payments Interface",
    "pa": "Payment Aggregator",
    "psp": "Payment System Provider",
    "pss": "Payment and Settlement Systems",
    "tat": "turnaround time",
    "afa": "Additional Factor of Authentication",
    "dpdp": "Digital Personal Data Protection",
    "npci": "National Payments Corporation of India",
    "rbi": "Reserve Bank of India",
    "cdd": "Customer Due Diligence",
    "ubo": "Ultimate Beneficial Owner",
}


def expand_query(query: str) -> list[str]:
    """Generate deterministic regulatory acronym and section-focused variants for RRF fusion."""
    variants = [query.strip()]
    tokens = re.findall(r"[A-Za-z0-9_:-]+", query)
    expansions = [
        _REGULATORY_EXPANSIONS[tok.lower()]
        for tok in tokens
        if tok.lower() in _REGULATORY_EXPANSIONS
    ]
    if expansions:
        variants.append(f"{query.strip()} {' '.join(dict.fromkeys(expansions))}")
    stripped = re.sub(r"\b(?:A|B):[a-z0-9_.-]+\b", "", query, flags=re.IGNORECASE).strip()
    if stripped and stripped != query.strip():
        variants.append(stripped)
    return list(dict.fromkeys(v for v in variants if v))


def rewrite_query(question: str, history: Sequence[Mapping[str, str]] = ()) -> str:
    """Resolve only evident follow-ups; ordinary queries remain untouched."""
    query = question.strip()
    if not history or not any(token in query.lower() for token in ("that ", "this ", "newer", "former", "latter")):
        return query
    prior = next((item.get("content", "").strip() for item in reversed(history) if item.get("content", "").strip()), "")
    return f"{query} (previous turn: {prior[:500]})" if prior else query
