from __future__ import annotations

import json
import os
import sqlite3
import time
from dataclasses import asdict
from pathlib import Path

from .models import AnalysisRecord


DB_PATH = Path(os.getenv("REPOLENS_DB", Path(__file__).parents[2] / "data" / "repolens.db"))


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("CREATE TABLE IF NOT EXISTS analyses (id TEXT PRIMARY KEY, repository TEXT NOT NULL, payload TEXT NOT NULL, created_at INTEGER NOT NULL)")
    connection.execute("CREATE TABLE IF NOT EXISTS traces (id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id TEXT NOT NULL, question TEXT NOT NULL, retrieved TEXT NOT NULL, latency_ms INTEGER NOT NULL, outcome TEXT NOT NULL, created_at INTEGER NOT NULL)")
    return connection


def save_analysis(record: AnalysisRecord) -> None:
    payload = json.dumps(asdict(record), separators=(",", ":"))
    with connect() as connection:
        connection.execute("INSERT OR REPLACE INTO analyses (id, repository, payload, created_at) VALUES (?, ?, ?, ?)", (record.id, f"{record.repo['owner']}/{record.repo['name']}", payload, int(time.time())))


def load_payload(analysis_id: str) -> dict | None:
    with connect() as connection:
        row = connection.execute("SELECT payload FROM analyses WHERE id = ?", (analysis_id,)).fetchone()
    return json.loads(row[0]) if row else None


def save_trace(analysis_id: str, question: str, retrieved: list[dict], latency_ms: int, outcome: str) -> None:
    with connect() as connection:
        connection.execute("INSERT INTO traces (analysis_id, question, retrieved, latency_ms, outcome, created_at) VALUES (?, ?, ?, ?, ?, ?)", (analysis_id, question, json.dumps(retrieved), latency_ms, outcome, int(time.time())))

