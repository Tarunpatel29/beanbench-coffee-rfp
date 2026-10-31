"""Checks model output before any numbers can affect the leaderboard."""
from __future__ import annotations

import json
import re


def parse_json_response(content: str) -> dict:
    """Parse plain JSON or JSON surrounded by a Markdown code fence."""
    if not isinstance(content, str):
        raise ValueError("The model did not return text.")
    cleaned = re.sub(r"^\s*```(?:json)?\s*|\s*```\s*$", "", content.strip(), flags=re.I)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("The model response did not contain a JSON object.")
        parsed = json.loads(cleaned[start:end + 1])
    if not isinstance(parsed, dict) or not isinstance(parsed.get("criteria"), list):
        raise ValueError("Expected a JSON object with a criteria list.")
    return parsed


def normalize_text(text: str) -> str:
    return " ".join(str(text).lower().split())


def validate_scorecard(raw: dict, supplier_name: str, criteria: list[dict], document_text: str) -> tuple[dict, list[str]]:
    """Fill omitted criteria with zero; clamp scores; verify quoted evidence."""
    warnings: list[str] = []
    by_id: dict[int, dict] = {}
    for item in raw.get("criteria", []):
        try:
            criterion_id = int(item.get("criterion_id"))
        except (AttributeError, TypeError, ValueError):
            warnings.append(f"{supplier_name}: ignored a criterion without a valid id.")
            continue
        if criterion_id in by_id:
            warnings.append(f"{supplier_name}: duplicate result for criterion {criterion_id}; kept the first.")
            continue
        by_id[criterion_id] = item
    active_ids = {int(c["criterion_id"]) for c in criteria}
    for unknown in sorted(set(by_id) - active_ids):
        warnings.append(f"{supplier_name}: ignored unknown criterion id {unknown}.")
    normalized = []
    for criterion in criteria:
        cid = int(criterion["criterion_id"])
        item = by_id.get(cid)
        valid = item is not None
        if item is None:
            item = {}
            warnings.append(f"{supplier_name}: missing {criterion['name']} score; set to 0 and excluded from benchmark.")
        value = item.get("score", 0)
        try:
            if isinstance(value, bool):
                raise ValueError
            score = float(value)
        except (TypeError, ValueError):
            score, valid = 0.0, False
            warnings.append(f"{supplier_name}: invalid {criterion['name']} score; set to 0 and excluded from benchmark.")
        maximum = float(criterion["max_score"])
        bounded = min(maximum, max(0.0, score))
        if bounded != score:
            warnings.append(f"{supplier_name}: {criterion['name']} score was clipped to 0–{maximum:g}.")
        evidence = str(item.get("evidence", "")).strip()
        verified = bool(evidence and normalize_text(evidence) in normalize_text(document_text))
        if evidence and not verified:
            warnings.append(f"{supplier_name}: evidence for {criterion['name']} was not found verbatim in the PDF text.")
        normalized.append({
            "criterion_id": cid, "name": criterion["name"], "description": criterion["description"],
            "weight": float(criterion["weight"]), "max_score": maximum,
            "score": round(bounded, 3), "valid_for_benchmark": valid,
            "justification": str(item.get("justification", "No justification returned.")),
            "evidence": evidence, "evidence_verified": verified,
        })
    return {"supplier_name": supplier_name, "criteria": normalized,
            "risks": raw.get("risks", []) if isinstance(raw.get("risks", []), list) else [],
            "overall_summary": str(raw.get("overall_summary", ""))}, warnings
