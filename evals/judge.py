from __future__ import annotations

from collections import Counter
import json
import os
import re


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to",
    "was", "were", "what", "which", "with",
}


def _terms(value: str) -> set[str]:
    return {
        term for term in re.findall(r"[a-z0-9]+", value.lower())
        if term not in _STOPWORDS and len(term) > 2
    }


def _lexical_judge(answer: str, reference: str, context: str) -> dict[str, object]:
    answer_terms = _terms(answer)
    reference_terms = _terms(reference)
    context_terms = _terms(context)
    overlap = len(answer_terms & reference_terms)
    precision = overlap / max(1, len(answer_terms))
    recall = overlap / max(1, len(reference_terms))
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    correctness = max(precision, f1)
    faithfulness = len(answer_terms & context_terms) / max(1, len(answer_terms)) if context_terms else (1.0 if not answer.strip() else 0.0)
    failure = "none"
    if not answer.strip():
        failure = "empty_answer"
    elif faithfulness < 0.5:
        failure = "ungrounded"
    elif correctness < 0.5:
        failure = "incorrect"
    return {"faithfulness": round(faithfulness, 4), "correctness": round(correctness, 4), "failure": failure}


def extract_key_facts(reference: str, max_facts: int = 4) -> list[str]:
    """Split a reference answer into 2-4 atomic required factual clauses."""
    clauses = [
        c.strip()
        for c in re.split(r"(?<=[.;])\s+|\s+[a-z]\)\s+", reference)
        if len(_terms(c)) >= 3
    ]
    if not clauses:
        return [reference.strip()] if reference.strip() else []
    if len(clauses) <= max_facts:
        return clauses
    # Keep evenly spaced key clauses up to max_facts
    step = len(clauses) / max_facts
    return [clauses[int(i * step)] for i in range(max_facts)]


def _fact_covered(fact: str, answer_terms: set[str], answer_nums: set[str]) -> bool:
    fact_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", fact))
    if fact_nums and not (fact_nums <= answer_nums):
        return False
    fact_terms = _terms(fact)
    if not fact_terms:
        return True
    return (len(fact_terms & answer_terms) / len(fact_terms)) >= 0.5


def judge_key_facts(
    answer: str,
    reference: str,
    context: str,
    required_facts: list[str] | None = None,
) -> dict[str, object]:
    """Key-facts rubric judge (2-4 required facts) with grounding check."""
    facts = required_facts if required_facts else extract_key_facts(reference)
    answer_terms = _terms(answer)
    answer_nums = set(re.findall(r"\b\d+(?:\.\d+)?\b", answer))
    context_terms = _terms(context)

    covered = sum(_fact_covered(fact, answer_terms, answer_nums) for fact in facts) if facts else 1
    correctness = covered / max(1, len(facts))
    faithfulness = (
        len(answer_terms & context_terms) / max(1, len(answer_terms))
        if context_terms
        else (1.0 if not answer.strip() else 0.0)
    )
    failure = "none"
    if not answer.strip():
        failure = "empty_answer"
    elif faithfulness < 0.5:
        failure = "ungrounded"
    elif correctness < 0.5:
        failure = "incorrect"
    return {
        "faithfulness": round(faithfulness, 4),
        "correctness": round(correctness, 4),
        "facts_total": len(facts),
        "facts_covered": covered,
        "failure": failure,
        "judge": "key_facts_rubric",
    }


def judge(answer: str, reference: str, context: str) -> dict[str, object]:
    """Context-only LLM judge, with deterministic offline fallback."""
    if os.getenv("RAG_KEY_FACTS_JUDGE") == "1":
        return judge_key_facts(answer, reference, context)
    if not os.getenv("COHERE_API_KEY"):
        return _lexical_judge(answer, reference, context)
    import time
    for attempt in range(3):
        try:
            from llm.providers.cohere import command_r_provider
            prompt = ("Return only JSON with numeric faithfulness and correctness from 0 to 1. "
                      "Judge only against CONTEXT, never outside knowledge.\n"
                      f"CONTEXT:\n{context}\nREFERENCE:\n{reference}\nANSWER:\n{answer}")
            raw, _, _ = command_r_provider(prompt)
            scores = json.loads(re.search(r"\{.*\}", raw, re.S).group())
            faithfulness, correctness = float(scores["faithfulness"]), float(scores["correctness"])
            failure = "none" if min(faithfulness, correctness) >= .5 else ("ungrounded" if faithfulness < .5 else "incorrect")
            return {"faithfulness": round(faithfulness, 4), "correctness": round(correctness, 4), "failure": failure, "judge": "llm"}
        except Exception:
            if attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue
            return {**_lexical_judge(answer, reference, context), "judge": "lexical_fallback"}


def summarize(results: list[dict[str, object]]) -> dict[str, object]:
    if not results:
        raise ValueError("at least one result is required")
    return {
        "questions": len(results),
        "faithfulness": round(sum(float(r["faithfulness"]) for r in results) / len(results), 4),
        "correctness": round(sum(float(r["correctness"]) for r in results) / len(results), 4),
        "failure_taxonomy": dict(Counter(str(r["failure"]) for r in results)),
    }
