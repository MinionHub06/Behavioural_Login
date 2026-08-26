import sqlite3
import json
from typing import Dict, Any, Optional
from app.models.base import get_db

def create_behavioural_baselines_table(conn: sqlite3.Connection) -> None:
    """Create the behavioural_baselines table if it does not exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS behavioural_baselines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            baseline_version INTEGER NOT NULL DEFAULT 1,
            status TEXT NOT NULL,
            sample_count INTEGER NOT NULL DEFAULT 0,
            keystroke_baseline_json TEXT NOT NULL,
            mouse_baseline_json TEXT NOT NULL,
            context_baseline_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.commit()

def save_or_update_baseline(user_id: int, baseline_data: Dict[str, Any]) -> int:
    """
    Saves or updates the rolling baseline record for a given user.
    If a baseline exists, updates fields and increments baseline_version.
    Returns the baseline record ID.
    """
    db = get_db()
    cursor = db.cursor()

    cursor.execute("SELECT id, baseline_version FROM behavioural_baselines WHERE user_id = ?", (user_id,))
    existing = cursor.fetchone()

    status = baseline_data.get('status', 'insufficient_data')
    sample_count = baseline_data.get('sample_count', 0)
    keystroke_json = json.dumps(baseline_data.get('keystroke', {}))
    mouse_json = json.dumps(baseline_data.get('mouse', {}))
    context_json = json.dumps(baseline_data.get('context', {}))

    if existing:
        new_version = existing['baseline_version'] + 1
        cursor.execute("""
            UPDATE behavioural_baselines
            SET baseline_version = ?,
                status = ?,
                sample_count = ?,
                keystroke_baseline_json = ?,
                mouse_baseline_json = ?,
                context_baseline_json = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (new_version, status, sample_count, keystroke_json, mouse_json, context_json, user_id))
        db.commit()
        return existing['id']
    else:
        cursor.execute("""
            INSERT INTO behavioural_baselines (
                user_id, baseline_version, status, sample_count,
                keystroke_baseline_json, mouse_baseline_json, context_baseline_json
            ) VALUES (?, 1, ?, ?, ?, ?, ?)
        """, (user_id, status, sample_count, keystroke_json, mouse_json, context_json))
        db.commit()
        return cursor.lastrowid

def get_user_baseline_record(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the current rolling baseline for a user, parsing JSON fields."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM behavioural_baselines WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return None

    row_dict = dict(row)
    return {
        'id': row_dict['id'],
        'user_id': row_dict['user_id'],
        'baseline_version': row_dict['baseline_version'],
        'status': row_dict['status'],
        'sample_count': row_dict['sample_count'],
        'keystroke': json.loads(row_dict['keystroke_baseline_json']),
        'mouse': json.loads(row_dict['mouse_baseline_json']),
        'context': json.loads(row_dict['context_baseline_json']),
        'created_at': row_dict['created_at'],
        'updated_at': row_dict['updated_at']
    }
