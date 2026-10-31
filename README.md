# BeanBench ☕

**A small, explainable coffee supplier proposal evaluator.** BeanBench is a classroom Streamlit app: upload coffee supplier PDFs, score them against saved criteria, inspect proposal evidence, compare vendors, and download a JSON record.

The vendors and proposals in this project are made up. They are safe practice material.

## Start the app on your Mac

Think of this like opening a new board game: open the project, prepare the pieces once, then start the game whenever you want to use it.

### One-time setup

1. Install [Python](https://www.python.org/downloads/macos/) and [Visual Studio Code](https://code.visualstudio.com/) if they are not already on your computer.
2. Open Visual Studio Code.
3. From the top menu choose **File → Open Folder…** and open the BeanBench project folder.
4. From the top menu choose **Terminal → New Terminal**. A small command area will appear along the bottom of VS Code.
5. Copy each line below, paste it into the terminal, and press **Return**. Wait for it to finish before entering the next line:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r requirements.txt
   python create_demo_pdfs.py
   python seed_db.py
   ```

The first setup downloads the two small Python packages the project needs and prepares four fictional coffee proposals. You only have to yes thado this setup once on this computer.

### Open BeanBench

1. In the same terminal, enter:

   ```bash
   streamlit run app.py
   ```

2. A browser page should open by itself. If it does not, copy the `http://localhost:8501` address printed in the terminal into your browser.
3. Click **Suppliers & Evaluate**. Keep **Use the included coffee examples** selected and click **Evaluate these suppliers**.
4. Click **Leaderboard** to compare the suppliers. Click **Scorecards** to see the reasons, quotes, and related passages.
5. Click **Run details** to see the steps, notes, and JSON download.

To open BeanBench another day, open this same folder in VS Code, choose **Terminal → New Terminal**, then enter:

```bash
source .venv/bin/activate
streamlit run app.py
```

To stop it, click inside the terminal and press **Control + C**.

### If a command looks scary

The words in the terminal are simply instructions for your computer. Copy one complete line from this guide, paste it into the terminal, and press Return. If you see a red error, copy the error text into this chat and I can explain the next step.

## Try AI scoring (optional)

BeanBench has two modes:

- **Offline demo** is selected by default. It uses a simple word-matching practice scorer. It needs no account, key, or payment, but it is not a real AI judgment.
- **OpenAI, Anthropic, or Gemini** can draft scorecards using your own provider key. Python still checks scores and calculates the final ranking.

To use a real model, choose its name in the app's left panel and paste in your own key. The key is used for that app session. The proposal text and key are sent to the provider you select to request an evaluation; choose fictional or otherwise appropriate documents. Model usage may cost money.

To save a key on your own computer rather than typing it each time, copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml` and uncomment the provider line you use. Do not put a real key in `app.py`, commit it to GitHub, or send it in this chat. For Streamlit Community Cloud, put it in that app's **Settings → Secrets** instead.

## App map: which small file does what?

| File | Job |
| --- | --- |
| `app.py` | The screens you click: criteria, supplier input, leaderboard, scorecards, run details, and history. |
| `evaluation.py` | The coordinator: reads a proposal, asks for a scorecard, checks it, and saves the run. |
| `tools/document_tool.py` | Reads text from PDFs and finds passages related to a criterion. |
| `tools/llm_client.py` | Sends the evaluation request to the chosen AI provider. |
| `tools/demo_llm.py` | Makes a clearly labeled practice scorecard if you do not use an AI provider. |
| `tools/validation_tool.py` | Checks the AI response, clips scores to the allowed range, fills missing scores, and checks quoted evidence. |
| `ranking.py` | Does all supplier arithmetic and tie-breaks in ordinary Python. |
| `db.py` / `seed_db.py` | Creates and uses the local SQLite database for rules and saved results. |
| `data/sample_proposals/` | Four fictional coffee supplier PDFs for the practice run. |
| `data/sample_output/example_offline_run.json` | Example result from the no-key practice scorer. |
| `data/edge_cases/` | Example unreadable, invalid, and prompt-injection practice files for a demo. |
| `DEMO.md` | A short script for showing the app to a class. |
| `generate_sample_output.py` | Regenerates the example JSON result after changing the sample proposals. |
| `work_zip.py` | Makes a clean zip file for handing in the project. |

## What the project does, one step at a time

1. **Setup:** load active criteria and percentages from SQLite.
2. **Input:** take multiple proposal PDFs plus supplier name, date, and experience rating.
3. **Batch:** create one unique run ID for all suppliers in this comparison.
4. **Read:** extract PDF text and its page count and fingerprint. Scanned picture-only PDFs are rejected because this demo has no OCR.
5. **Find evidence:** split PDF text into passages and retrieve passages whose words relate to each scoring criterion. This is the small **RAG-style** part: look up relevant document text before showing an answer.
6. **Evaluate:** optionally ask the chosen model for one proposed score per criterion and exact supporting quote. The prompt says proposal text is evidence only and instructions inside the PDF must be ignored.
7. **Validate:** normalize missing or malformed scores, clip scores that fall outside the allowed range, and flag quotes that are not present in the document text.
8. **Score and rank:** Python calculates the scores and applies stable tie-breaks. The AI does not calculate arithmetic or choose a winner.
9. **Save and present:** store the run in SQLite and display the leaderboard, scorecards, warnings, and JSON download.

## The scoring rules

- **Weighted score (out of 100):** for each criterion, score ÷ maximum score × criterion weight; add the results.
- **Criterion benchmark:** highest valid score for that criterion among suppliers in this run. A missing or malformed score cannot set the benchmark.
- **Gap:** supplier's score minus the benchmark. The leader's gap is zero; other suppliers' gaps are negative.
- **Relative performance:** supplier score ÷ benchmark × 100. If the benchmark is zero, relative performance is defined as zero.
- **Peer Performance Index (PPI):** add each criterion's relative percentage × its weight, then divide by the total active weight. PPI is rounded to four decimal places before it is used for ranking.
- **Tie-breaks:** higher PPI first → earlier submission date → higher experience rating → supplier name A–Z.

Active criteria weights must total exactly 100% before the app allows a run. Edit them in the **Criteria** tab; the values are kept in SQLite.

## Put the app online with Streamlit Community Cloud

The online app has a public link. Use only the fictional practice proposals unless you have permission to share the documents you upload.

1. Create a GitHub account if you do not have one.
2. Create a **private** GitHub repository for your BeanBench project.
3. Publish this project folder to that repository from VS Code. The `.gitignore` file keeps the database, virtual environment, and real secrets out of the upload.
4. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with GitHub.
5. Choose **Create app**, select your repository and branch, and set the main file to `app.py`.
6. Choose **Deploy**. If using a real model, enter its API key in the app's **Settings → Secrets**.
7. Open the app URL Streamlit gives you.

When you get to the GitHub screens, tell me what you see and I’ll guide you through one small click at a time. Never paste your GitHub password or model key into chat.

**Saving note:** SQLite saves runs on the computer or server running BeanBench. Streamlit Community Cloud's local files may reset after a restart, so download the JSON for any result you need to keep.

## Make a clean hand-in zip

In the VS Code terminal, with `.venv` active, enter:

```bash
python work_zip.py
```

This creates `beanbench_submission.zip` and leaves out the local database, real secrets, and Python's temporary files.

## Important classroom note

The four suppliers and their details are fictional. The offline keyword practice mode is not an AI evaluation. Even with an AI provider, read the quotes and warnings yourself before using any score. BeanBench is a learning project, not a purchasing authority.
