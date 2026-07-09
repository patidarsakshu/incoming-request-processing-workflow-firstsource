import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "case_log.db")


def init_db():
    """Creates the case_log table if it doesn't already exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS case_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            request_id TEXT,
            raw_text TEXT,
            request_type TEXT,
            urgency TEXT,
            sub_topic TEXT,
            confidence TEXT,
            reasoning TEXT,
            steps_executed TEXT,
            draft_response TEXT,
            routing_team TEXT,
            follow_up TEXT,
            status TEXT,
            processed_at TEXT
        )
    """)
    conn.commit()
    conn.close()


def log_case(raw_text: str, classification, remediation):
    """Inserts a processed request + its outcome into the audit trail."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO case_log (
            request_id, raw_text, request_type, urgency, sub_topic,
            confidence, reasoning, steps_executed, draft_response,
            routing_team, follow_up, status, processed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        remediation.request_id,
        raw_text,
        classification.request_type,
        classification.urgency,
        classification.sub_topic,
        classification.confidence,
        classification.reasoning,
        json.dumps(remediation.steps_executed),
        remediation.draft_response,
        remediation.routing_team,
        remediation.follow_up,
        remediation.status,
        remediation.processed_at,
    ))
    conn.commit()
    conn.close()


def get_all_cases():
    """Returns all logged cases as a list of dicts (for dashboard)."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM case_log ORDER BY id DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_summary_counts():
    """Returns request volume by type and by status — for the dashboard."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT request_type, COUNT(*) FROM case_log GROUP BY request_type")
    by_type = dict(cursor.fetchall())

    cursor.execute("SELECT status, COUNT(*) FROM case_log GROUP BY status")
    by_status = dict(cursor.fetchall())

    conn.close()
    return {"by_type": by_type, "by_status": by_status}