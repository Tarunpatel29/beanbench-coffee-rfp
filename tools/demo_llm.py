"""Offline classroom stand-in. It is a keyword heuristic, not a language model."""
from __future__ import annotations

import re
from tools.document_tool import retrieve_evidence


def evaluate(text: str, supplier_name: str, criteria: list[dict]) -> dict:
    words = set(re.findall(r"[a-z0-9]+", text.lower()))
    results = []
    for criterion in criteria:
        query = criterion["name"] + " " + criterion["description"]
        evidence = retrieve_evidence(text, query, 1)
        terms = set(re.findall(r"[a-z0-9]+", query.lower()))
        match_count = len(terms & words)
        score = min(float(criterion["max_score"]), max(2.0, 3.5 + min(match_count, 6) * 0.75 + (1.0 if evidence else 0)))
        results.append({"criterion_id": criterion["criterion_id"], "score": round(score, 1),
                        "justification": "Offline practice estimate based on matching proposal words; please review.",
                        "evidence": evidence[0] if evidence else ""})
    return {"supplier_name": supplier_name, "criteria": results,
            "risks": ["Offline keyword estimate used; this is not an AI judgment."],
            "overall_summary": "Practice scorecard created by the offline demo evaluator. Review the evidence before use."}
