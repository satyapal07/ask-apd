"""
Query memory — Pinterest's "query history as knowledge base" step.

Stores every successful question→code pair in SQLite.
On each new question, retrieves the top-K most similar past queries
and injects them as few-shot examples into the prompt.

This is the self-reinforcing loop: every query the system answers
makes it better at answering similar questions in the future.
"""

import sqlite3
import os
import json
from datetime import datetime

_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "catalog", "query_history.db")


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            question    TEXT NOT NULL,
            tables_used TEXT NOT NULL,   -- JSON array
            pandas_code TEXT NOT NULL,
            chart_type  TEXT,
            explanation TEXT,
            success     INTEGER DEFAULT 1,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_question ON query_history(question)")
    conn.commit()
    return conn


def save_query(question: str, tables_used: list[str], pandas_code: str,
               chart_type: str = None, explanation: str = None, success: bool = True):
    """Persist a question→code pair after successful execution."""
    conn = _get_conn()
    conn.execute(
        """INSERT INTO query_history (question, tables_used, pandas_code, chart_type, explanation, success)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (question, json.dumps(tables_used), pandas_code, chart_type, explanation, int(success))
    )
    conn.commit()
    conn.close()


def find_similar(question: str, top_k: int = 3) -> list[dict]:
    """
    Retrieve the top-K most relevant past queries.

    Uses keyword overlap scoring (Pinterest uses vector embeddings;
    this is the lightweight version — swap in ChromaDB/FAISS later).
    Only returns successful queries.
    """
    conn = _get_conn()
    rows = conn.execute(
        "SELECT question, tables_used, pandas_code, chart_type, explanation FROM query_history WHERE success=1 ORDER BY id DESC LIMIT 200"
    ).fetchall()
    conn.close()

    if not rows:
        return []

    # Tokenize query
    q_tokens = set(question.lower().split())
    # Remove stop words
    stop = {'what','which','how','show','me','the','a','an','of','by','for',
            'is','are','in','on','and','or','to','get','give','list','find'}
    q_tokens -= stop

    scored = []
    for row in rows:
        past_q, tables_json, code, chart_type, explanation = row
        past_tokens = set(past_q.lower().split()) - stop
        overlap = len(q_tokens & past_tokens)
        if overlap > 0:
            scored.append((overlap, {
                "question":    past_q,
                "tables_used": json.loads(tables_json),
                "pandas_code": code,
                "chart_type":  chart_type,
                "explanation": explanation,
            }))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [item for _, item in scored[:top_k]]


def build_few_shot_context(similar: list[dict]) -> str:
    """
    Format past queries as few-shot examples for injection into the prompt.
    This is Pinterest's "structural & statistical patterns" step.
    """
    if not similar:
        return ""

    lines = ["── SIMILAR PAST QUERIES (use as examples) ──"]
    for i, ex in enumerate(similar, 1):
        lines.append(f"\nExample {i}:")
        lines.append(f"  Question: {ex['question']}")
        lines.append(f"  Tables:   {ex['tables_used']}")
        lines.append(f"  Code:     {ex['pandas_code'][:300]}{'...' if len(ex['pandas_code']) > 300 else ''}")
        if ex.get("chart_type") and ex["chart_type"] != "none":
            lines.append(f"  Chart:    {ex['chart_type']}")
    lines.append("── END EXAMPLES ──")
    return "\n".join(lines)


def get_stats() -> dict:
    """Return summary stats about the query history."""
    conn = _get_conn()
    total   = conn.execute("SELECT COUNT(*) FROM query_history").fetchone()[0]
    success = conn.execute("SELECT COUNT(*) FROM query_history WHERE success=1").fetchone()[0]
    conn.close()
    return {"total": total, "successful": success}
