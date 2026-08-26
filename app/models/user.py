import sqlite3
from typing import Optional, Dict, Any
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.base import get_db

def create_users_table(conn: sqlite3.Connection) -> None:
    """Create the users table if it does not already exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()

def create_user(username: str, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Hashes password securely and inserts a new user into SQLite using parameterized queries.
    Returns the created user dict or None if creation fails.
    """
    password_hash = generate_password_hash(password)
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
            (username.strip(), email.strip().lower(), password_hash)
        )
        db.commit()
        user_id = cursor.lastrowid
        return get_user_by_id(user_id)
    except sqlite3.IntegrityError:
        db.rollback()
        return None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """Fetch user by username using parameterized SQL query."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username.strip(),))
    row = cursor.fetchone()
    return dict(row) if row else None

def get_user_by_email(email: str) -> Optional[Dict[str, Any]]:
    """Fetch user by email using parameterized SQL query."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email.strip().lower(),))
    row = cursor.fetchone()
    return dict(row) if row else None

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch user by primary key ID using parameterized SQL query."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT id, username, email, password_hash, created_at FROM users WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    return dict(row) if row else None

def verify_user_password(user: Dict[str, Any], password: str) -> bool:
    """Verify raw password against stored password hash using Werkzeug security."""
    if not user or 'password_hash' not in user:
        return False
    return check_password_hash(user['password_hash'], password)
