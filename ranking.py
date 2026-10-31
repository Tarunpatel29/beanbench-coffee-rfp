"""Transparent supplier arithmetic and deterministic ranking (no AI calls here)."""
from __future__ import annotations


def rank_suppliers(scorecards: list[dict]) -> tuple[list[dict], dict]:
    """Add benchmarks, gaps, relative scores, weighted totals, PPI, and ranks."""
    if not scorecards:
        return [], {"benchmarks": {}, "formula": "No successful supplier scorecards."}
    weights = sum(float(item["weight"]) for item in scorecards[0]["criteria"])
    if weights <= 0:
        raise ValueError("Active criterion weights must add up to more than zero.")
    benchmarks = {}
    for item in scorecards[0]["criteria"]:
        cid = item["criterion_id"]
        valid_scores = [criterion["score"] for card in scorecards for criterion in card["criteria"]
                        if criterion["criterion_id"] == cid and criterion["valid_for_benchmark"]]
        benchmarks[cid] = max(valid_scores) if valid_scores else 0.0
    rows = []
    for original in scorecards:
        row = {**original, "criteria": [dict(item) for item in original["criteria"]]}
        absolute = weighted_relative = 0.0
        for item in row["criteria"]:
            benchmark = benchmarks[item["criterion_id"]]
            relative = (item["score"] / benchmark * 100) if benchmark else 0.0
            weighted_points = item["score"] / item["max_score"] * item["weight"]
            item.update(benchmark=round(benchmark, 3), gap=round(item["score"] - benchmark, 3),
                        relative_percent=round(relative, 2), weighted_points=round(weighted_points, 2))
            absolute += weighted_points
            weighted_relative += relative * item["weight"]
        row["absolute_score"] = round(absolute, 2)
        row["ppi"] = round(weighted_relative / weights, 4)
        rows.append(row)
    # PPI is rounded before sorting so floating-point noise cannot beat a real tie-break rule.
    rows.sort(key=lambda r: (-r["ppi"], r["submission_date"], -r["experience_rating"], r["supplier_name"].casefold()))
    for rank, row in enumerate(rows, 1):
        row["final_rank"] = rank
        row["tie_break_reason"] = "Top-ranked supplier." if rank == 1 else _why_ahead(rows[rank - 2], row)
    return rows, {"benchmarks": benchmarks,
                  "formula": "PPI = sum(relative performance % × criterion weight) ÷ active weight total; zero benchmark gives 0%.",
                  "tie_break_order": ["higher PPI (rounded to 4 decimals)", "earlier submission date",
                                      "higher experience rating", "supplier name A–Z"]}


def _why_ahead(ahead: dict, behind: dict) -> str:
    if ahead["ppi"] != behind["ppi"]:
        return f"PPI was higher ({ahead['ppi']:.4f} vs {behind['ppi']:.4f})."
    if ahead["submission_date"] != behind["submission_date"]:
        return f"PPI tied; submitted earlier ({ahead['submission_date']} vs {behind['submission_date']})."
    if ahead["experience_rating"] != behind["experience_rating"]:
        return f"PPI and date tied; experience rating was higher ({ahead['experience_rating']:g} vs {behind['experience_rating']:g})."
    return f"PPI, date, and experience tied; {ahead['supplier_name']} comes first alphabetically."
