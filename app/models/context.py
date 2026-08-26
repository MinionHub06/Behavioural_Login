import sqlite3
from typing import Dict, Any, List
from app.models.base import get_db

def create_context_features_table(conn: sqlite3.Connection) -> None:
    """Create the context_features table if it does not exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS context_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            device_id TEXT NOT NULL,
            device_status TEXT NOT NULL,
            ip_address TEXT NOT NULL,
            location TEXT NOT NULL,
            location_status TEXT NOT NULL,
            login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            login_hour INTEGER NOT NULL,
            time_status TEXT NOT NULL,
            new_device BOOLEAN NOT NULL,
            new_location BOOLEAN NOT NULL,
            unusual_time BOOLEAN NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.commit()

def save_context_features(context_data: Dict[str, Any]) -> int:
    """
    Saves a evaluated context feature record for a user into SQLite.
    Returns inserted row ID.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO context_features (
            user_id, device_id, device_status, ip_address, location,
            location_status, login_time, login_hour, time_status,
            new_device, new_location, unusual_time
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        int(context_data['user_id']),
        str(context_data['device_id']),
        str(context_data['device_status']),
        str(context_data['ip_address']),
        str(context_data['location']),
        str(context_data['location_status']),
        str(context_data['login_time']),
        int(context_data['login_hour']),
        str(context_data['time_status']),
        bool(context_data['new_device']),
        bool(context_data['new_location']),
        bool(context_data['unusual_time'])
    ))
    db.commit()
    return cursor.lastrowid

def get_user_context_features(user_id: int) -> List[Dict[str, Any]]:
    """Retrieve all historical contextual login records for a user."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM context_features WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
