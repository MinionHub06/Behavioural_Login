import sqlite3
import math
from typing import Optional, Dict, Any, Tuple
from pathlib import Path
from app.models.base import get_db

# Sensitivity & Validation Constants
MIN_SAMPLE_COUNT = 1
MAX_DWELL_TIME_MS = 10000.0     # Max reasonable key press duration
MAX_FLIGHT_TIME_MS = 60000.0    # Max reasonable inter-keystroke duration
MAX_DURATION_MS = 300000.0      # Max 5 minute typing session

REQUIRED_KEYSTROKE_FIELDS = [
    'avg_dwell_time', 'std_dwell_time', 'min_dwell_time', 'max_dwell_time',
    'avg_flight_time', 'std_flight_time', 'min_flight_time', 'max_flight_time',
    'total_typing_duration', 'typing_speed', 'typing_speed_variance',
    'sample_count'
]

def create_keystroke_features_table(conn: sqlite3.Connection) -> None:
    """Create the keystroke_features table if it does not exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keystroke_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            avg_dwell_time REAL NOT NULL,
            std_dwell_time REAL NOT NULL,
            min_dwell_time REAL NOT NULL,
            max_dwell_time REAL NOT NULL,
            avg_flight_time REAL NOT NULL,
            std_flight_time REAL NOT NULL,
            min_flight_time REAL NOT NULL,
            max_flight_time REAL NOT NULL,
            total_typing_duration REAL NOT NULL,
            typing_speed REAL NOT NULL,
            typing_speed_variance REAL NOT NULL,
            sample_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.commit()

def validate_keystroke_features(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Strictly validates the keystroke feature payload.
    Ensures data type correctness, positive bounds, non-NaN/Inf, and reasonable ranges.
    Returns (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Payload must be a JSON object."

    for field in REQUIRED_KEYSTROKE_FIELDS:
        if field not in data:
            return False, f"Missing required feature: '{field}'."
        
        val = data[field]
        # Ensure values are int or float and not boolean
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            return False, f"Field '{field}' must be a numeric value."
        
        # Reject NaN and Infinity
        if math.isnan(val) or math.isinf(val):
            return False, f"Field '{field}' contains invalid numeric value (NaN or Infinity)."

    # Sample count validation
    sample_count = data['sample_count']
    if not isinstance(sample_count, int) or sample_count < MIN_SAMPLE_COUNT:
        return False, f"Field 'sample_count' must be an integer >= {MIN_SAMPLE_COUNT}."

    # Range and Non-negative validation for timing metrics
    for field in ['avg_dwell_time', 'std_dwell_time', 'min_dwell_time', 'max_dwell_time',
                  'avg_flight_time', 'std_flight_time', 'min_flight_time', 'max_flight_time',
                  'total_typing_duration', 'typing_speed', 'typing_speed_variance']:
        if data[field] < 0:
            return False, f"Field '{field}' cannot be negative."

    if data['max_dwell_time'] > MAX_DWELL_TIME_MS:
        return False, f"Dwell time exceeds maximum threshold ({MAX_DWELL_TIME_MS}ms)."

    if data['total_typing_duration'] > MAX_DURATION_MS:
        return False, f"Total typing duration exceeds maximum threshold ({MAX_DURATION_MS}ms)."

    return True, ""

def save_keystroke_features(user_id: int, features: Dict[str, Any]) -> Optional[int]:
    """
    Saves validated aggregate keystroke features for a user into SQLite.
    Returns inserted row ID or None on failure.
    """
    is_valid, err = validate_keystroke_features(features)
    if not is_valid:
        raise ValueError(err)

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO keystroke_features (
            user_id, avg_dwell_time, std_dwell_time, min_dwell_time, max_dwell_time,
            avg_flight_time, std_flight_time, min_flight_time, max_flight_time,
            total_typing_duration, typing_speed, typing_speed_variance, sample_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        float(features['avg_dwell_time']),
        float(features['std_dwell_time']),
        float(features['min_dwell_time']),
        float(features['max_dwell_time']),
        float(features['avg_flight_time']),
        float(features['std_flight_time']),
        float(features['min_flight_time']),
        float(features['max_flight_time']),
        float(features['total_typing_duration']),
        float(features['typing_speed']),
        float(features['typing_speed_variance']),
        int(features['sample_count'])
    ))
    db.commit()
    return cursor.lastrowid

def get_user_keystroke_features(user_id: int):
    """Retrieve all historical keystroke feature samples for a user."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM keystroke_features WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
