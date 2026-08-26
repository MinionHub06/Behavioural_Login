import sqlite3
import json
from typing import Dict, Any, Optional
from app.models.base import get_db

def create_risk_scores_table(conn: sqlite3.Connection) -> None:
    """Create the risk_scores table if it does not exist, and ensure explanation columns exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            keystroke_score REAL,
            mouse_score REAL,
            device_score REAL,
            location_score REAL,
            time_score REAL,
            risk_score REAL,
            status TEXT NOT NULL,
            signals_json TEXT NOT NULL,
            explanation_json TEXT,
            explanation_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    # Ensure schema migration for existing development database tables
    cursor.execute("PRAGMA table_info(risk_scores);")
    existing_cols = [col[1] for col in cursor.fetchall()]
    if 'explanation_json' not in existing_cols:
        cursor.execute("ALTER TABLE risk_scores ADD COLUMN explanation_json TEXT;")
    if 'explanation_summary' not in existing_cols:
        cursor.execute("ALTER TABLE risk_scores ADD COLUMN explanation_summary TEXT;")

    conn.commit()

def save_risk_score(user_id: int, risk_eval: Dict[str, Any]) -> int:
    """
    Saves a calculated risk score evaluation and explanation for a user into SQLite.
    Returns inserted row ID.
    """
    db = get_db()
    cursor = db.cursor()

    signals = risk_eval.get('signals', {})
    ks_score = signals.get('keystroke', {}).get('score') if isinstance(signals.get('keystroke'), dict) else None
    ms_score = signals.get('mouse', {}).get('score') if isinstance(signals.get('mouse'), dict) else None
    dev_score = signals.get('device', {}).get('score') if isinstance(signals.get('device'), dict) else None
    loc_score = signals.get('location', {}).get('score') if isinstance(signals.get('location'), dict) else None
    tm_score = signals.get('time', {}).get('score') if isinstance(signals.get('time'), dict) else None

    risk_score_val = risk_eval.get('risk_score')
    status_str = risk_eval.get('status', 'unevaluated')
    signals_json = json.dumps(signals)

    explanation = risk_eval.get('explanation')
    explanation_json = json.dumps(explanation) if explanation else None
    explanation_summary = explanation.get('summary') if isinstance(explanation, dict) else None

    cursor.execute("""
        INSERT INTO risk_scores (
            user_id, keystroke_score, mouse_score, device_score,
            location_score, time_score, risk_score, status, signals_json,
            explanation_json, explanation_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, ks_score, ms_score, dev_score,
        loc_score, tm_score, risk_score_val, status_str, signals_json,
        explanation_json, explanation_summary
    ))
    db.commit()
    return cursor.lastrowid

def get_latest_user_risk_score(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the latest risk evaluation and explanation record for a user."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM risk_scores WHERE user_id = ? ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return None

    row_dict = dict(row)
    explanation_data = json.loads(row_dict['explanation_json']) if row_dict.get('explanation_json') else None

    return {
        'id': row_dict['id'],
        'user_id': row_dict['user_id'],
        'keystroke_score': row_dict['keystroke_score'],
        'mouse_score': row_dict['mouse_score'],
        'device_score': row_dict['device_score'],
        'location_score': row_dict['location_score'],
        'time_score': row_dict['time_score'],
        'risk_score': row_dict['risk_score'],
        'status': row_dict['status'],
        'signals': json.loads(row_dict['signals_json']) if row_dict.get('signals_json') else {},
        'explanation': explanation_data,
        'explanation_summary': row_dict.get('explanation_summary'),
        'created_at': row_dict['created_at']
    }
