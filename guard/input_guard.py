from __future__ import annotations

import re

from guard.redact import redact_pii

_INJECTION_PATTERNS = [
    # Direct instruction override attempts
    re.compile(r"\b(ignore|disregard|override|forget|bypass|skip)\b.*\b(instructions|system prompt|rules|guidelines|constraints|safety)\b", re.IGNORECASE),
    # Role hijacking / jailbreak role-play
    re.compile(r"\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be|switch\s+to|enter)\b.*\b(unrestricted|unfiltered|jailbreak|DAN|mode|developer)\b", re.IGNORECASE),
    re.compile(r"\b(developer\s+mode|do\s+anything\s+now|jailbreak)\b", re.IGNORECASE),
    # System/prompt leaking attempts
    re.compile(r"\b(reveal|show|print|output|dump|display|repeat|leak)\b.*\b(system\s*prompt|internal|api\s*key|secret|password|hidden|instructions)\b", re.IGNORECASE),
    # Encoded/obfuscated injection markers
    re.compile(r"(?:base64|rot13|hex|encode|decode)\s*[:=]", re.IGNORECASE),
    # Delimiter / markup escape attempts
    re.compile(r"<\s*/?\s*(?:script|iframe|img|svg|style|system|prompt)\b", re.IGNORECASE),
    # Multi-line instruction block injection
    re.compile(r"```\s*(?:system|instruction|prompt)", re.IGNORECASE),
    # Hindi / Hinglish prompt-injection & override patterns
    re.compile(r"\b(pichle|purane|pehle\s+ke|saare|sab)\b.*\b(nirdesh|niyam|instructions|rules)\b.*\b(bhool|chhod|ignore|hata|badal)\b", re.IGNORECASE),
    re.compile(r"\b(bhool\s+jao|ignore\s+karo|hata\s+do|bypass\s+karo)\b.*\b(niyam|nirdesh|prompt|rules|instructions)\b", re.IGNORECASE),
    re.compile(r"\b(system\s*prompt|secret|api\s*key|internal\s+rules)\b.*\b(dikhao|batao|nikalo|print\s+karo|bhejo)\b", re.IGNORECASE),
]

_BORDERLINE_MARKERS = re.compile(
    r"\b(jailbreak|bypass|override|system\s*prompt|developer\s*mode|unrestricted|secret|password|api\s*key|hypothetically|roleplay|pretend)\b",
    re.IGNORECASE,
)


def _second_layer_check(question: str) -> bool:
    """Second-layer check for borderline queries (returns True if unsafe).

    Uses an optional LLM classifier when RAG_LLM_GUARD=1 and COHERE_API_KEY are set;
    otherwise applies deterministic structural intent scoring on borderline markers.
    """
    if not _BORDERLINE_MARKERS.search(question):
        return False
    import os
    if os.getenv("RAG_LLM_GUARD") == "1" and os.getenv("COHERE_API_KEY"):
        try:
            from llm.providers.cohere import command_r_provider
            verdict, _, _ = command_r_provider(
                "Classify as SAFE or UNSAFE (prompt injection / jailbreak / secret exfiltration). "
                f"Reply with one word.\nQuery: {question}"
            )
            return "UNSAFE" in verdict.upper()
        except Exception:
            pass
    # Deterministic intent check: borderline marker + imperative/exfiltration verb
    imperative = re.search(r"\b(tell|show|give|ignore|act|pretend|answer|explain|disable|turn\s+off|follow)\b", question, re.IGNORECASE)
    return bool(imperative)
_DOMAIN_TERMS = re.compile(
    r"\b(rbi|npci|upi|kyc|aml|pmla|payment|aggregator|ppi|wallet|"
    r"prepaid|bank|circular|master direction|regulated|transaction|"
    r"mandate|remittance|forex|customer due diligence|passage|section|"
    r"incident|response|appellate|tribunal|officer|requirement|direction|"
    r"rule|guideline|framework|nodal|cyber|security|liability|account|"
    r"consent|card|customer|dispute|grievance|fraud|penalty|audit|board)\b",
    re.IGNORECASE,
)
_CORPUS_DOCUMENT_ID = re.compile(
    r"\b(?:A|B):(?:pa|ppi|kyc|cyber|emandate|auth|upi|pss|pmla|dpdp|data_storage|cust_liability|tat)[a-z0-9_:-]*",
    re.IGNORECASE,
)


class UnsupportedQuestionError(ValueError):
    pass


def check_input(question: str) -> str:
    if not question.strip():
        raise ValueError("question must not be empty")
    if len(question) > 4000:
        raise ValueError("question is too long")
    question = redact_pii(question).strip()
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(question):
            raise ValueError("prompt injection detected")
    if _second_layer_check(question):
        raise ValueError("prompt injection detected (second-layer)")
    if not _DOMAIN_TERMS.search(question) and not _CORPUS_DOCUMENT_ID.search(question):
        raise UnsupportedQuestionError("question is outside the regulatory corpus")
    return question
