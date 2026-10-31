"""Small SQLite helpers. The database file is created automatically on first run."""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "beanbench.db"
DEFAULT_CRITERIA = [
    ("Product quality", "Bean quality, consistency, certifications, tasting or lab evidence", 25, 10),
    ("Supply reliability", "Capacity, sourcing continuity, backup plans, delivery reliability", 20, 10),
    ("Implementation plan", "Onboarding milestones, schedule, named owners, and practical rollout", 20, 10),
    ("Commercial value", "Price clarity, total cost, payment terms, and assumptions", 15, 10),
    ("Food safety & traceability", "Food safety controls, certifications, lot traceability, and audits", 12, 10),
    ("Support & experience", "Relevant customer experience, references, and support response times", 8, 10),
]


def connect(db_path: str | Path | None = None) -> sqlite3.Connection:
    con = sqlite3.connect(db_path or DB_PATH)
    con.row_factory = sqlite3.Row
    return con


def initialize_db(db_path: str | Path | None = None) -> None:
    with connect(db_path) as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS evaluation_criteria (
            criterion_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE, description TEXT NOT NULL,
            weight REAL NOT NULL, max_score REAL NOT NULL DEFAULT 10,
            is_active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS rfp_runs (
            rfp_run_id TEXT PRIMARY KEY, created_at TEXT NOT NULL,
            status TEXT NOT NULL, llm_provider TEXT NOT NULL,
            llm_model TEXT NOT NULL, run_json TEXT NOT NULL DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS supplier_results (
            result_id INTEGER PRIMARY KEY AUTOINCREMENT,
            rfp_run_id TEXT NOT NULL, supplier_name TEXT NOT NULL,
            submission_date TEXT NOT NULL, experience_rating REAL NOT NULL,
            absolute_score REAL, ppi REAL, final_rank INTEGER,
            result_json TEXT NOT NULL,
            FOREIGN KEY(rfp_run_id) REFERENCES rfp_runs(rfp_run_id)
        );
        """)
        # Upgrade the first BeanBench starter's database, if it already exists.
        existing = {row[1] for row in con.execute("PRAGMA table_info(rfp_runs)")}
        for column, definition in (("llm_provider", "TEXT NOT NULL DEFAULT 'Offline demo'"),
                                  ("llm_model", "TEXT NOT NULL DEFAULT 'offline-keyword-demo'"),
                                  ("run_json", "TEXT NOT NULL DEFAULT '{}'")):
            if column not in existing:
                con.execute(f"ALTER TABLE rfp_runs ADD COLUMN {column} {definition}")
        if con.execute("SELECT COUNT(*) FROM evaluation_criteria").fetchone()[0] == 0:
            con.executemany(
                "INSERT INTO evaluation_criteria(name,description,weight,max_score,is_active) VALUES(?,?,?,?,1)",
                DEFAULT_CRITERIA,
            )


def get_criteria(active_only: bool = False, db_path: str | Path | None = None) -> list[dict]:
    where = "WHERE is_active=1" if active_only else ""
    with connect(db_path) as con:
        return [dict(row) for row in con.execute(
            f"SELECT * FROM evaluation_criteria {where} ORDER BY criterion_id"
        )]


def save_criteria(rows: list[dict], db_path: str | Path | None = None) -> None:
    with connect(db_path) as con:
        for row in rows:
            con.execute(
                "UPDATE evaluation_criteria SET description=?,weight=?,max_score=?,is_active=? WHERE criterion_id=?",
                (str(row["description"]), float(row["weight"]), float(row["max_score"]),
                 int(row["is_active"]), int(row["criterion_id"])),
            )


def create_run(provider: str, model: str, db_path: str | Path | None = None) -> str:
    run_id = str(uuid.uuid4())
    with connect(db_path) as con:
        con.execute("INSERT INTO rfp_runs(rfp_run_id,created_at,status,llm_provider,llm_model) VALUES(?,?,?,?,?)",
                    (run_id, datetime.now().astimezone().isoformat(timespec="seconds"), "running", provider, model))
    return run_id


def save_run(run_id: str, status: str, result: dict, db_path: str | Path | None = None) -> None:
    with connect(db_path) as con:
        con.execute("UPDATE rfp_runs SET status=?,run_json=? WHERE rfp_run_id=?",
                    (status, json.dumps(result, ensure_ascii=False), run_id))
        all_rows = list(result.get("suppliers", [])) + list(result.get("failed_suppliers", []))
        for row in all_rows:
            con.execute("""INSERT INTO supplier_results
                (rfp_run_id,supplier_name,submission_date,experience_rating,absolute_score,ppi,final_rank,result_json)
                VALUES(?,?,?,?,?,?,?,?)""",
                (run_id, row["supplier_name"], row.get("submission_date", ""), row.get("experience_rating", 0),
                 row.get("absolute_score"), row.get("ppi"), row.get("final_rank"),
                 json.dumps(row, ensure_ascii=False)))


def list_runs(limit: int = 30, db_path: str | Path | None = None) -> list[dict]:
    with connect(db_path) as con:
        return [dict(row) for row in con.execute(
            "SELECT rfp_run_id,created_at,status,llm_provider,llm_model FROM rfp_runs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )]


def load_run(run_id: str, db_path: str | Path | None = None) -> dict | None:
    with connect(db_path) as con:
        row = con.execute("SELECT run_json FROM rfp_runs WHERE rfp_run_id=?", (run_id,)).fetchone()
    return json.loads(row[0]) if row else None
