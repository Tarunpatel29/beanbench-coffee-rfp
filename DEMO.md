# BeanBench demonstration guide

Use the **Offline demo** provider so the walkthrough needs no account, API key, or paid model.

1. Start BeanBench and open **Suppliers & Evaluate**.
2. Keep **Use the included coffee examples** selected and click **Evaluate these suppliers**.
3. Open **Leaderboard** and explain weighted score, PPI, and the tie-break reason.
4. Open **Scorecards**, select a supplier, then expand a criterion to see its score, supporting quote, evidence check, and related passages.
5. Open **Run details** and point out the sequence of steps, validation notes, PDF fingerprint, and JSON download.
6. To demonstrate editable business rules, open **Criteria**, change one weight, adjust another so the active total is still 100%, and click **Save scoring rules**.
7. To demonstrate an input error, choose **Upload my own PDFs** and try the included `data/edge_cases/not_a_pdf.pdf` or `scanned_no_text.pdf`. The error should say why it could not be read. Return to the sample pack for the successful run.
8. The `prompt_injection_practice.pdf` file can demonstrate that proposal instructions are treated as document text rather than evaluation instructions when using a real AI provider. Don't upload that example as evidence of model behavior in Offline demo mode.

**Be transparent in the demonstration:** Offline demo makes a keyword-based practice scorecard, not a real AI judgment. Mention that the LLM is optional and Python is responsible for the score formulas and final ranking.
