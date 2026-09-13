import sqlite3
import time
from typing import Optional, Dict, Any
from app.models.base import get_db

def create_otp_table(conn: sqlite3.Connection) -> None:
    """Creates the user_otps table for step-up verification."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            otp_code TEXT NOT NULL,
            expires_at REAL NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            is_used INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.commit()

def save_otp(user_id: int, otp_code: str, expires_at: float) -> int:
    """Invalidates older unused OTPs for the user and saves a new active OTP."""
    db = get_db()
    cursor = db.cursor()
    
    # Invalidate older active OTPs
    cursor.execute("UPDATE user_otps SET is_used = 1 WHERE user_id = ? AND is_used = 0", (user_id,))
    
    cursor.execute("""
        INSERT INTO user_otps (user_id, otp_code, expires_at, attempts, is_used)
        VALUES (?, ?, ?, 0, 0)
    """, (user_id, str(otp_code), float(expires_at)))
    db.commit()
    return cursor.lastrowid

def get_latest_otp(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves the latest unused OTP record for a user."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM user_otps
        WHERE user_id = ? AND is_used = 0
        ORDER BY id DESC LIMIT 1
    """, (user_id,))
    row = cursor.fetchone()
    if not row:
        return None
    return dict(row)

def increment_otp_attempts(otp_id: int) -> int:
    """Increments failed verification attempts counter and returns new count."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE user_otps SET attempts = attempts + 1 WHERE id = ?", (otp_id,))
    cursor.execute("SELECT attempts FROM user_otps WHERE id = ?", (otp_id,))
    row = cursor.fetchone()
    db.commit()
    return row['attempts'] if row else 0

def mark_otp_used(otp_id: int) -> None:
    """Marks OTP as successfully used."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("UPDATE user_otps SET is_used = 1 WHERE id = ?", (otp_id,))
    db.commit()

def delete_user_otps(user_id: int) -> None:
    """Deletes all OTP records for a user."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("DELETE FROM user_otps WHERE user_id = ?", (user_id,))
    db.commit()
