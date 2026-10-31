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
.stApp{background:#f5f7f9;color:#2d3a45;font-family:'DM Sans',sans-serif}
h1,h2,h3{font-family:'Fraunces',serif;color:#283f55}
[data-testid='stHeader']{background:rgba(245,247,249,.9)}
[data-testid='stSidebar']{background:linear-gradient(180deg,#233b53 0%,#344f68 100%)}
[data-testid='stSidebar'] [data-testid='stMarkdownContainer'],[data-testid='stSidebar'] label,[data-testid='stSidebar'] h1,[data-testid='stSidebar'] h2,[data-testid='stSidebar'] h3,[data-testid='stSidebar'] p{color:#f4f2ed!important}
[data-testid='stSidebar'] [data-testid='stCaptionContainer']{color:#cbd6df!important}
[data-testid='stMetric']{background:#fff;border:1px solid #dfe6ec;padding:16px;border-radius:16px;box-shadow:0 5px 18px rgba(35,59,83,.05)}
[data-testid='stMetricLabel']{color:#687783}
[data-testid='stButton'] button:not(:disabled),[data-testid='stDownloadButton'] button:not(:disabled){background:#405c75!important;color:#fff!important;border:1px solid #405c75!important;border-radius:11px;font-weight:700;opacity:1!important;transition:all .18s ease}
[data-testid='stButton'] button:not(:disabled):hover,[data-testid='stDownloadButton'] button:not(:disabled):hover{background:#304a62!important;color:#fff!important;border-color:#304a62!important;transform:translateY(-1px)}
[data-testid='stButton'] button:disabled,[data-testid='stDownloadButton'] button:disabled{background:#dce3e9!important;color:#4b5d6d!important;border:1px solid #cbd5de!important;border-radius:11px;font-weight:700;opacity:1!important}
[data-testid='stTabs'] button{color:#536f88;font-weight:600}
[data-testid='stTabs'] [aria-selected='true']{border-bottom-color:#927d91!important}
[data-testid='stDataFrame'],[data-testid='stDataEditor']{border:1px solid #dfe6ec;border-radius:14px;overflow:hidden}
[data-testid='stImage'] img{border-radius:22px;height:245px;object-fit:cover;object-position:82% center}
.bb-hero{position:relative;overflow:hidden;background:linear-gradient(135deg,#263f56 0%,#536a80 100%);border:1px solid rgba(255,255,255,.22);border-radius:26px;padding:30px 34px 26px;margin:12px 0 18px;color:#fff;box-shadow:0 16px 34px rgba(35,59,83,.13);min-height:245px;display:flex;flex-direction:column;justify-content:center}
.bb-hero:after{content:'';position:absolute;width:300px;height:300px;border:1px solid rgba(255,255,255,.1);border-radius:50%;right:-130px;top:-175px;box-shadow:0 0 0 28px rgba(255,255,255,.025),0 0 0 58px rgba(255,255,255,.02)}
.bb-kicker{font-size:.76rem;letter-spacing:.16em;text-transform:uppercase;color:#d9c5b8;font-weight:700;margin-bottom:9px}
.bb-title{font-family:'Fraunces',serif;font-size:clamp(2.25rem,4vw,3.25rem);line-height:1.05;font-weight:700;color:#fff;margin:0 0 8px}
.bb-subtitle{font-size:1.03rem;color:#d9ebe4;margin:0;max-width:760px}
.bb-badge{display:inline-block;margin-top:17px;margin-right:6px;padding:6px 11px;border-radius:999px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.10);font-size:.78rem;color:#f4f2ed}
.bb-step{min-height:82px;border:1px solid #dfe6ec;border-radius:15px;background:#fff;padding:12px 14px;box-shadow:0 4px 14px rgba(35,59,83,.04)}
.bb-step.active{border-color:#a99bad;background:#f8f5f9}
.bb-step.done{border-color:#c6d5df;background:#edf3f7}
.bb-step-title{font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;color:#74808a;font-weight:700}
.bb-step-value{font-size:.95rem;color:#30485c;font-weight:700;margin-top:5px}
.bb-section{border-bottom:1px solid #dfe6ec;padding-bottom:9px;margin-bottom:14px}
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
    st.markdown("#### Criterion score breakdown")
    criterion_rows = [{"Criterion": row["name"], "Score": row["score"]} for row in supplier["criteria"]]
    st.bar_chart(criterion_rows, x="Criterion", y="Score", horizontal=True,
                 color="#927d91", height=290, x_label="Score")
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
                with st.expander("Find related proposal passages"):
                    for passage in passages:
                        st.write("> " + passage)
            elif not document_text:
                st.caption("Re-upload the proposal to search related passages for this saved scorecard.")
    if supplier.get("risks"):
        st.warning("Risks or missing details: " + "; ".join(supplier["risks"]))


current_run = st.session_state.get("beanbench_current_run")
active_criteria = db.get_criteria(active_only=True)
active_weight_total = sum(float(item["weight"]) for item in active_criteria)
sample_count = len(list(SAMPLE_DIR.glob("*.pdf")))
has_run = bool(current_run)
hero_copy, hero_photo = st.columns([1.25, 1], gap="small")
with hero_copy:
    st.markdown("""
<section class="bb-hero">
  <div class="bb-kicker">BeanBench · Coffee Supplier Review</div>
  <div class="bb-title">A clearer way to compare suppliers.</div>
  <p class="bb-subtitle">Review coffee proposals against consistent criteria, trace every score to evidence, and keep the final decision in human hands.</p>
  <span class="bb-badge">☕ Sample proposal set</span>
  <span class="bb-badge">⌕ Evidence-led review</span>
  <span class="bb-badge">✓ Human-reviewed decisions</span>
</section>
""", unsafe_allow_html=True)
with hero_photo:
    st.image(str(ROOT / "assets" / "coffee-roastery-hero.png"), caption="Coffee cupping · supplier quality review", use_container_width=True)

criteria_ready = abs(active_weight_total - 100) < .01
journey = [
    ("01 · Criteria", "Weights set" if criteria_ready else "Review weights", criteria_ready),
    ("02 · Proposals", f"{sample_count} sample proposals ready" if not has_run else "Proposals reviewed", has_run),
    ("03 · Evaluation", "Completed" if has_run else "Ready when you are", has_run),
    ("04 · Decision", "Review the evidence" if has_run else "Pending evaluation", has_run),
]
journey_cols = st.columns(4)
for index, (label, value, complete) in enumerate(journey):
    style = "done" if complete else ("active" if index == (3 if has_run else 1) else "")
    journey_cols[index].markdown(
        f'<div class="bb-step {style}"><div class="bb-step-title">{label}</div><div class="bb-step-value">{"✓ " if complete else ""}{value}</div></div>',
        unsafe_allow_html=True,
    )
st.write("")

with st.sidebar:
    st.markdown("### ⚙️ Review settings")
    st.caption("Choose how proposal scorecards are drafted.")
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
    st.caption("The language model drafts scorecards. Python verifies evidence, calculates weighted scores, and ranks suppliers.")

criteria_tab, input_tab, leaderboard_tab, scorecards_tab, details_tab, history_tab = st.tabs([
    "⚖️ Criteria", "📄 Suppliers & Evaluate", "🏆 Leaderboard", "🧾 Scorecards", "🔍 Run details", "🕓 History"
])

with criteria_tab:
    st.subheader("Scoring criteria")
    st.write("Set the buying team's priorities. Active weights must add up to 100% before a fair comparison can run.")
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
    total_col, save_col = st.columns([1, 2])
    total_col.metric("Active weight total", f"{total:g}%", delta="Ready" if abs(total - 100) < .01 else "Adjust to 100%")
    with save_col:
        if st.button("Save scoring rules", type="primary", use_container_width=True):
            db.save_criteria(edited_rows)
            st.success("Saved. These rules will be used for the next evaluation.")
            st.rerun()
    with st.expander("View the weight distribution"):
        st.caption("Each active criterion contributes this share of the final supplier score.")
        active_rows = [row for row in edited_rows if row["is_active"]]
        weight_cols = st.columns(3)
        for index, row in enumerate(active_rows):
            with weight_cols[index % 3]:
                weight = max(0.0, min(100.0, float(row["weight"])))
                st.markdown(f"**{row['name']}** · {weight:g}%")
                st.progress(weight / 100)

with input_tab:
    input_intro, input_photo = st.columns([1.5, .8], gap="large")
    with input_intro:
        st.subheader("Supplier proposals")
        st.caption("Compare vendor offers against the same criteria, then review the evidence behind every score.")
        mode = st.radio("Proposal source", ["Use the included sample proposals", "Upload my own PDFs"], horizontal=True)
    with input_photo:
        st.image(str(ROOT / "assets" / "coffee-quality-review.png"), caption="Green coffee quality inspection", use_container_width=True)
    if mode == "Use the included sample proposals":
        examples = sample_files()
        st.info(f"{len(examples)} sample supplier proposals are ready for evaluation. Compare their strengths across the criteria below.")
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
        leaders = result["suppliers"]
        if leaders:
            top = leaders[0]
            metric_cols = st.columns(3)
            metric_cols[0].metric("Suppliers reviewed", len(leaders))
            metric_cols[1].metric("Top-ranked supplier", top["supplier_name"])
            metric_cols[2].metric("Leading weighted score", f"{top['absolute_score']}/100")
            st.markdown("#### Overall supplier comparison")
            chart_rows = [{"Supplier": row["supplier_name"], "Weighted score": row["absolute_score"]} for row in leaders]
            st.bar_chart(chart_rows, x="Supplier", y="Weighted score", horizontal=True,
                         color="#607d98", height=250, x_label="Score out of 100")
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
        selected_supplier = next(row for row in result["suppliers"] if row["supplier_name"] == selected)
        display_scorecard(selected_supplier)
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
