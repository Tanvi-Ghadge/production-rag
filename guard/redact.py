from __future__ import annotations

import re

_PATTERNS = (
    (r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b", "[REDACTED_EMAIL]"),
    (r"\b(?:\+?91[-\s]?)?[6-9]\d{9}\b", "[REDACTED_PHONE]"),
    (r"\b\d{12}\b", "[REDACTED_AADHAAR]"),
    (r"\b[A-Z]{5}\d{4}[A-Z]\b", "[REDACTED_PAN]"),       # Indian PAN card
    (r"\b[A-Z]{4}0[A-Z0-9]{6}\b", "[REDACTED_IFSC]"),     # Bank IFSC code
    (r"\b\d{9,18}\b(?=.*account)", "[REDACTED_ACCOUNT]"),  # Bank account numbers
)


def redact_pii(text: str) -> str:
    for pattern, replacement in _PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text