"""Write an illustrative offline-mode JSON export for the four included proposals."""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

import db
from create_demo_pdfs import PROPOSALS
from ranking import rank_suppliers
from tools.demo_llm import evaluate
from tools.validation_tool import validate_scorecard

ROOT = Path(__file__).parent
SAMPLE_METADATA = {
    "Apex Coffee Co.": ("2026-10-05", 4.2),
    "BrightPath Beans": ("2026-10-08", 2.5),
    "NexaWorks Coffee Supply": ("2026-10-06", 4.0),
    "Orbit Digital Roasters": ("2026-10-07", 4.6),
}

if __name__ == "__main__":
    criteria = [dict(criterion_id=i, name=row[0], description=row[1], weight=row[2], max_score=row[3], is_active=1)
                for i, row in enumerate(db.DEFAULT_CRITERIA, start=1)]
    cards, warnings = [], []
    for supplier, pages in PROPOSALS.items():
        text = re.sub(r"\s+", " ", " ".join(pages)).strip()
        raw = evaluate(text, supplier, criteria)
        card, notes = validate_scorecard(raw, supplier, criteria, text)
        submitted, experience = SAMPLE_METADATA[supplier]
        card.update(submission_date=submitted, experience_rating=experience,
                    filename=re.sub(r"[^a-z0-9]+", "_", supplier.lower()).strip("_") + "_proposal.pdf", page_count=len(pages),
                    extracted_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest())
        cards.append(card)
        warnings.extend(notes)
    ranked, ranking_info = rank_suppliers(cards)
    warnings.insert(0, "Offline keyword practice scores are illustrative and are not AI judgments.")
    run_id = "sample-offline-coffee-run"
    result = {
        "rfp_run_id": run_id,
        "created_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": "completed_with_warnings",
        "provider": "Offline demo",
        "model": "offline-keyword-demo",
        "suppliers": ranked,
        "failed_suppliers": [],
        "warnings": warnings,
        "trace": [
            {"step": "Setup", "status": "complete", "detail": f"Loaded {len(criteria)} active criteria."},
            {"step": "Input", "status": "complete", "detail": "Received four fictional coffee proposals."},
            {"step": "Evaluate & validate", "status": "complete", "detail": "Generated and normalized offline practice scorecards."},
            {"step": "Score & benchmark", "status": "complete", "detail": "Calculated weighted totals and peer metrics in Python."},
            {"step": "Rank", "status": "complete", "detail": "Applied the brief's deterministic tie-break order."},
        ],
        "ranking": ranking_info,
    }
    output = ROOT / "data" / "sample_output" / "example_offline_run.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Created {output}")
