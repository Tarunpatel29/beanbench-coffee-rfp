"""BeanBench: a beginner-friendly coffee supplier RFP review desk."""
from __future__ import annotations

import csv
import io
import json
import re
from pathlib import Path

import streamlit as st

import db
from evaluation import run_pipeline
from tools.document_tool import extract_pdf, retrieve_evidence

ROOT = Path(__file__).parent
SAMPLE_DIR = ROOT / "data" / "sample_proposals"

st.set_page_config(page_title="BeanBench · Supplier Review", page_icon="☕", layout="wide")
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Fraunces:wght@500;600;700&display=swap');
.stApp{background:#f7f4ee;color:#263b32;font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Fraunces',serif;color:#234337}
[data-testid='stMetric']{background:#fff;border:1px solid #e6dfd2;padding:16px;border-radius:14px}
.stButton>button{background:#28634c;color:#fff;border-radius:10px;border:0;font-weight:600}
[data-testid='stTabs'] button{color:#28634c}
</style>""", unsafe_allow_html=True)

db.initialize_db()
criteria = db.get_criteria()


def secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def sample_files() -> list[dict]:
    records = []
    with (ROOT / "data" / "sample_metadata.csv").open(encoding="utf-8", newline="") as source:
        metadata = {row["filename"]: row for row in csv.DictReader(source)}
    for path in sorted(SAMPLE_DIR.glob("*.pdf")):
        row = metadata.get(path.name, {})
        name = row.get("supplier_name", path.stem.replace("_", " ").title())
        submitted = row.get("submission_date", "2026-10-05")
        experience = float(row.get("experience_rating", 3.0))
        records.append({"supplier_name": name, "submission_date": submitted, "experience_rating": experience,
                        "file_name": path.name, "bytes": path.read_bytes()})
    return records


def display_scorecard(supplier: dict) -> None:
    st.markdown(f"### {supplier['supplier_name']} · Rank {supplier['final_rank']}")
    st.write(supplier.get("overall_summary", ""))
    st.caption(f"Weighted score: **{supplier['absolute_score']}/100** · Peer Performance Index: **{supplier['ppi']}/100** · Rank reason: {supplier.get('tie_break_reason','')}")
    columns = ["name", "score", "max_score", "weight", "weighted_points", "benchmark", "gap", "relative_percent", "evidence_verified"]
    st.dataframe([{key: row.get(key) for key in columns} for row in supplier["criteria"]], hide_index=True, use_container_width=True)
    for criterion in supplier["criteria"]:
        label = f"{criterion['name']} · {criterion['score']}/{criterion['max_score']}"
        with st.expander(label):
            st.write("**Why this score:** " + criterion.get("justification", ""))
            quote = criterion.get("evidence", "")
            st.write("**Quoted evidence:** “" + (quote or "No exact quote was returned.") + "”")
            st.caption("Evidence was found in proposal text." if criterion.get("evidence_verified") else "The quote could not be matched to proposal text; check it manually.")
            document_text = st.session_state.get("beanbench_document_texts", {}).get(supplier["supplier_name"], "")
            passages = retrieve_evidence(document_text, criterion["name"] + " " + criterion.get("description", ""), 3)
            if passages:
                with st.expander("Find related proposal passages (RAG-style)"):
                    for passage in passages:
                        st.write("> " + passage)
            elif not document_text:
                st.caption("Re-upload the proposal to search related passages for this saved scorecard.")
    if supplier.get("risks"):
        st.warning("Risks or missing details: " + "; ".join(supplier["risks"]))


st.title("☕ BeanBench")
st.caption("Coffee supplier proposals, reviewed with evidence · fictional classroom data · human-reviewed decisions")

with st.sidebar:
    st.header("AI settings")
    provider = st.selectbox("Who should draft the scorecards?", ["Offline demo", "OpenAI", "Anthropic", "Gemini"])
    key_names = {"OpenAI": "OPENAI_API_KEY", "Anthropic": "ANTHROPIC_API_KEY", "Gemini": "GEMINI_API_KEY"}
    model_defaults = {"OpenAI": "gpt-4o-mini", "Anthropic": "claude-3-5-haiku-latest", "Gemini": "gemini-2.0-flash"}
    model = "offline-keyword-demo"
    api_key = ""
    base_url = ""
    if provider != "Offline demo":
        key_name = key_names[provider]
        api_key = st.text_input("API key (kept in this session)", value=secret(key_name), type="password", help="This key is sent to the provider you selected so it can evaluate the proposals.")
        model = st.text_input("Model name", value=model_defaults[provider])
        base_url = st.text_input("Optional custom endpoint", value="", help="Leave blank to use the provider's usual address.")
        if not api_key:
            st.info("Add your own key to use AI, or choose Offline demo. Offline mode needs no account or payment.")
    st.divider()
    st.caption("The AI reviews proposal wording. Python checks scores and makes the final calculations and ranking.")

criteria_tab, input_tab, leaderboard_tab, scorecards_tab, details_tab, history_tab = st.tabs([
    "⚖️ Criteria", "📄 Suppliers & Evaluate", "🏆 Leaderboard", "🧾 Scorecards", "🔍 Run details", "🕓 History"
])

with criteria_tab:
    st.subheader("Scoring criteria")
    st.write("Change what matters to your coffee buying team. Active weights must add up to 100% before evaluation.")
    criteria = db.get_criteria()
    editor = st.data_editor(criteria, hide_index=True, use_container_width=True,
                            disabled=["criterion_id", "name"],
                            column_config={
                                "criterion_id": st.column_config.NumberColumn("ID", width="small"),
                                "name": st.column_config.TextColumn("Criterion", width="medium"),
                                "description": st.column_config.TextColumn("What to look for", width="large"),
                                "weight": st.column_config.NumberColumn("Weight (%)", min_value=0, max_value=100, step=1),
                                "max_score": st.column_config.NumberColumn("Max score", min_value=1, max_value=100, step=1),
                                "is_active": st.column_config.CheckboxColumn("Active"),
                            })
    edited_rows = editor.to_dict("records") if hasattr(editor, "to_dict") else editor
    total = sum(float(row["weight"]) for row in edited_rows if row["is_active"])
    st.metric("Active weight total", f"{total:g}%", delta="Ready" if abs(total - 100) < .01 else "Adjust to 100%")
    if st.button("Save scoring rules"):
        db.save_criteria(edited_rows)
        st.success("Saved. These rules will be used for the next evaluation.")
        st.rerun()

with input_tab:
    st.subheader("Bring in proposals")
    mode = st.radio("Where should the proposals come from?", ["Use the included coffee examples", "Upload my own PDFs"], horizontal=True)
    if mode == "Use the included coffee examples":
        examples = sample_files()
        st.info(f"Ready to use {len(examples)} fictional supplier proposals. Each has a different strength and weakness.")
        st.dataframe([{"Supplier": x["supplier_name"], "PDF": x["file_name"], "Date submitted": x["submission_date"], "Experience / 5": x["experience_rating"]} for x in examples], hide_index=True, use_container_width=True)
        suppliers = examples
    else:
        uploads = st.file_uploader("Select two or more supplier proposal PDFs", type=["pdf"], accept_multiple_files=True)
        suppliers = []
        if uploads:
            st.caption("Edit the supplier details. The name will be used on the leaderboard.")
            for index, upload in enumerate(uploads):
                columns = st.columns([2, 1, 1])
                guess = re.sub(r"[_-]+", " ", Path(upload.name).stem).replace("proposal", "").strip().title()
                name = columns[0].text_input("Supplier name", guess, key=f"supplier_name_{index}")
                submitted = columns[1].date_input("Submission date", key=f"supplier_date_{index}")
                experience = columns[2].slider("Experience / 5", 0.0, 5.0, 3.0, .1, key=f"supplier_experience_{index}")
                suppliers.append({"supplier_name": name.strip(), "submission_date": submitted.isoformat(),
                                  "experience_rating": experience, "file_name": upload.name, "bytes": upload.getvalue()})
    active = db.get_criteria(active_only=True)
    total = sum(float(item["weight"]) for item in active)
    st.info(f"Current active weights: **{total:g}%**. The brief requires 100%.")
    valid_names = all(x["supplier_name"].strip() for x in suppliers)
    valid_experience = all(0 <= float(x["experience_rating"]) <= 5 for x in suppliers)
    unique_names = len({x["supplier_name"].casefold() for x in suppliers}) == len(suppliers)
    can_run = len(suppliers) >= 2 and abs(total - 100) < .01 and valid_names and valid_experience and unique_names
    if st.button("Evaluate these suppliers", type="primary", use_container_width=True, disabled=not can_run):
        if provider != "Offline demo" and not api_key:
            st.error("Add an API key in the left panel, or choose Offline demo.")
        else:
            with st.spinner("Reading PDFs, checking evidence, then calculating the leaderboard…"):
                prepared = []
                for supplier in suppliers:
                    item = {k: supplier[k] for k in ("supplier_name", "submission_date", "experience_rating", "file_name")}
                    item["file"] = io.BytesIO(supplier["bytes"])
                    item["file"].name = supplier["file_name"]
                    prepared.append(item)
                try:
                    result = run_pipeline(prepared, provider, api_key, model, base_url)
                    # Keep proposal text in this app session only; do not add it to saved results or downloads.
                    retrieved_texts = {}
                    for supplier in prepared:
                        document = extract_pdf(supplier["file"])
                        retrieved_texts[supplier["supplier_name"]] = document["text"]
                    st.session_state["beanbench_document_texts"] = retrieved_texts
                    st.session_state["beanbench_current_run"] = result
                    st.success("Evaluation complete. Open the Leaderboard or Scorecards tabs above.")
                except Exception as exc:
                    st.error(f"This run could not be completed: {exc}")
    if not can_run:
        if len(suppliers) < 2: st.caption("Add at least two suppliers so the app can compare them.")
        elif abs(total - 100) >= .01: st.caption("Adjust active criterion weights to total 100% in the Criteria tab.")
        elif not valid_names: st.caption("Enter a name for each supplier.")
        elif not valid_experience: st.caption("Experience rating must be between 0 and 5.")
        else: st.caption("Give each supplier a different name.")

with leaderboard_tab:
    result = st.session_state.get("beanbench_current_run")
    if not result:
        st.info("Evaluate proposals first. Your supplier ranking will show here.")
    else:
        st.subheader("The supplier leaderboard")
        st.caption(f"Run: `{result['rfp_run_id']}` · ranking uses validated scores and the tie-break rules in your brief.")
        st.dataframe([{"Rank": row["final_rank"], "Supplier": row["supplier_name"],
                       "Weighted score / 100": row["absolute_score"], "PPI / 100": row["ppi"],
                       "Submitted": row["submission_date"], "Experience / 5": row["experience_rating"],
                       "Why this rank?": row["tie_break_reason"]} for row in result["suppliers"]], hide_index=True, use_container_width=True)
        if result["failed_suppliers"]:
            st.warning("These suppliers could not be ranked: " + "; ".join(x["supplier_name"] for x in result["failed_suppliers"]))

with scorecards_tab:
    result = st.session_state.get("beanbench_current_run")
    if not result:
        st.info("Supplier scorecards appear after an evaluation.")
    elif result["suppliers"]:
        selected = st.selectbox("Choose a supplier", [row["supplier_name"] for row in result["suppliers"]])
        display_scorecard(next(row for row in result["suppliers"] if row["supplier_name"] == selected))
    else:
        st.warning("No supplier had a complete scorecard to display.")

with details_tab:
    result = st.session_state.get("beanbench_current_run")
    if not result:
        st.info("Run details, validation notes, and downloads appear after an evaluation.")
    else:
        st.subheader("What the app did")
        st.write(f"**Run ID:** `{result['rfp_run_id']}`  ·  **Status:** {result['status']}  ·  **Evaluator:** {result['provider']} / {result['model']}")
        st.markdown("**Ranking formula:** " + result["ranking"]["formula"])
        st.markdown("**Tie-break order:** " + " → ".join(result["ranking"]["tie_break_order"]))
        st.dataframe(result["trace"], hide_index=True, use_container_width=True)
        if result["warnings"]:
            st.warning("Review notes: " + " · ".join(result["warnings"]))
        else:
            st.success("No validation warnings were recorded.")
        for supplier_name, audit in result["audit"].items():
            with st.expander(f"Technical record · {supplier_name}"):
                st.caption(f"Proposal fingerprint (SHA-256): {audit['document_sha256']}")
                st.code(audit["raw_model_output"], language="json")
        st.download_button("Download the complete run as JSON", json.dumps(result, indent=2, ensure_ascii=False),
                           file_name=f"beanbench_{result['rfp_run_id'][:8]}.json", mime="application/json")

with history_tab:
    st.subheader("Past evaluations")
    runs = db.list_runs()
    if not runs:
        st.info("Your saved runs will appear here.")
    else:
        st.dataframe(runs, hide_index=True, use_container_width=True)
        selected_run = st.selectbox("Load a saved run", [item["rfp_run_id"] for item in runs], key="history_run")
        if st.button("Show this saved run"):
            st.session_state["beanbench_current_run"] = db.load_run(selected_run)
            st.success("Loaded. Open the Leaderboard, Scorecards, or Run details tab.")
