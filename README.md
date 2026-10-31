# BeanBench ☕

### Coffee supplier proposal evaluation and comparison

BeanBench helps a buying team compare supplier proposals against shared scoring criteria. It extracts evidence from proposal PDFs, prepares explainable scorecards, checks the results, and calculates a consistent supplier ranking.

- **Live app:** [BeanBench on Streamlit](https://tarunpatel29-beanbench-coffee-rfp-app-pi5nd9.streamlit.app/)
- **Source code:** [BeanBench on GitHub](https://github.com/Tarunpatel29/beanbench-coffee-rfp)

> The included coffee suppliers and proposals are sample data. BeanBench is an educational decision-support project; a person should review the evidence and make the final decision.

## What you can do

- Set evaluation criteria and weights, with a 100% total required before a run.
- Compare the included coffee proposals or upload supplier PDFs.
- Review scorecards with supporting quotes and related passages from each proposal.
- See supplier rankings, criterion-level comparisons, and run details.
- Save evaluation history locally and download a JSON record.
- Choose a no-key offline demonstration mode or connect an AI provider with your own key.

## How an evaluation works

1. **Set the rules.** Choose active criteria and weights in the Criteria tab. Active weights must add up to 100%.
2. **Add proposals.** Use the sample proposals or upload multiple supplier PDFs.
3. **Read and retrieve evidence.** BeanBench extracts PDF text and finds passages related to each criterion. This is a lightweight retrieval-augmented generation (RAG-style) step: relevant source text is gathered before a scorecard is drafted.
4. **Draft and check scorecards.** The selected AI provider may suggest criterion scores and supporting quotes. Validation checks score ranges and whether the quoted evidence appears in the proposal. The offline demo uses keyword matching and does not make real AI judgments.
5. **Calculate and rank.** Python applies the scoring formula and tie-break rules, then saves and displays the results. The model does not calculate the final ranking.
6. **Review the result.** Use the Leaderboard, Scorecards, Run details, and History tabs to inspect the outcome.

## Scoring and ranking

- **Weighted score (out of 100):** for each criterion, divide the supplier's score by the maximum score, multiply by that criterion's weight, then add the results.
- **Criterion benchmark:** the highest valid supplier score for a criterion in the current run.
- **Gap:** supplier score minus the criterion benchmark. The leader's gap is zero.
- **Relative performance:** supplier score divided by the benchmark, multiplied by 100. If the benchmark is zero, relative performance is zero.
- **Peer Performance Index (PPI):** the weighted average of criterion-level relative performance, rounded to four decimal places for ranking.
- **Tie-break order:** higher PPI, earlier submission date, higher experience rating, then supplier name A–Z.

## Technology and project structure

BeanBench is built with Python, Streamlit, and SQLite. PDF text extraction, evidence retrieval, validation, scoring, ranking, and storage are organized into separate modules.

| File or folder | Purpose |
| --- | --- |
| `app.py` | Streamlit interface and project tabs |
| `evaluation.py` | Coordinates proposal evaluation and saving results |
| `tools/document_tool.py` | Extracts PDF text and retrieves relevant passages |
| `tools/llm_client.py` | Connects to the selected AI provider |
| `tools/demo_llm.py` | Creates clearly labeled keyword-based demo scorecards |
| `tools/validation_tool.py` | Checks scorecards and evidence quotes |
| `ranking.py` | Calculates scores, PPI, rankings, and tie-breaks |
| `db.py`, `seed_db.py` | SQLite storage and starting criteria |
| `data/sample_proposals/` | Included sample coffee supplier proposals |
| `data/edge_cases/` | Example files for input and prompt-handling demonstrations |
| `DEMO.md` | Optional walkthrough of the main app features |

## Run BeanBench on your computer

### One-time setup

1. Install [Python](https://www.python.org/downloads/macos/) and [Visual Studio Code](https://code.visualstudio.com/) if needed.
2. In Visual Studio Code, choose **File → Open Folder…** and open the BeanBench project folder.
3. Choose **Terminal → New Terminal**.
4. Copy and run these lines one at a time, waiting for each line to finish:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python create_demo_pdfs.py
   python seed_db.py
   ```

### Start the app

In the same terminal, run:

```bash
streamlit run app.py
```

Open the local address shown in the terminal if the app does not open automatically. In the app, use the included proposals, evaluate them, then explore the Leaderboard and Scorecards tabs.

To start it again later, open the project folder in VS Code, open a new terminal, and run:

```bash
source .venv/bin/activate
streamlit run app.py
```

To stop the local app, click in the terminal and press **Control + C**.

## AI provider and privacy notes

The **Offline demo** mode is selected by default. It requires no API key and uses simple keyword matching for practice; it is not a real AI evaluation.

OpenAI, Anthropic, and Gemini can be selected to draft scorecards with your own provider key. The app's password-masked key field keeps the key in that session. The proposal text is sent to the provider you select, and provider usage may cost money. Do not place a real API key in source code, commit it to GitHub, or share it in chat. For a deployed app, you can optionally add a provider key to the app's Streamlit Community Cloud secrets; the app reads the matching `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, or `GEMINI_API_KEY` setting.

SQLite stores results on the computer or server running BeanBench. Streamlit Community Cloud's local files may reset after a restart, so download the JSON record for any result you need to keep.

## Scope and limitations

- Image-only scanned PDFs are not supported because OCR is not included.
- Evidence retrieval is a lightweight word-based method, not a vector database.
- AI-generated scorecards can be wrong; check the cited proposal text and warnings.
- Sample suppliers and proposals are fictional. Use documents only when you have permission to upload them.
- BeanBench is a learning project and decision-support aid, not a purchasing authority.

## Optional class demonstration

See [`DEMO.md`](DEMO.md) for a short walkthrough of a successful evaluation, scorecard evidence, editable criteria, and an input-error example.
