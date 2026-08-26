import sqlite3
import math
from typing import Optional, Dict, Any, Tuple
from app.models.base import get_db

# Sensitivity & Validation Constants
MIN_POINT_COUNT = 3
MAX_VELOCITY_PX_SEC = 50000.0       # Max realistic cursor velocity (px/sec)
MAX_ACCEL_PX_SEC2 = 1000000.0       # Max realistic cursor acceleration (px/sec^2)
MAX_TRACKING_DURATION_MS = 600000.0 # Max 10 minute tracking duration

REQUIRED_MOUSE_FIELDS = [
    'avg_velocity', 'std_velocity', 'min_velocity', 'max_velocity',
    'avg_acceleration', 'std_acceleration',
    'avg_curvature', 'std_curvature', 'total_direction_change',
    'jitter_score',
    'pause_count', 'avg_pause_duration', 'max_pause_duration', 'total_pause_duration',
    'total_path_length', 'tracking_duration', 'point_count'
]

def create_mouse_features_table(conn: sqlite3.Connection) -> None:
    """Create the mouse_features table if it does not exist."""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mouse_features (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            avg_velocity REAL NOT NULL,
            std_velocity REAL NOT NULL,
            min_velocity REAL NOT NULL,
            max_velocity REAL NOT NULL,
            avg_acceleration REAL NOT NULL,
            std_acceleration REAL NOT NULL,
            avg_curvature REAL NOT NULL,
            std_curvature REAL NOT NULL,
            total_direction_change REAL NOT NULL,
            jitter_score REAL NOT NULL,
            pause_count INTEGER NOT NULL,
            avg_pause_duration REAL NOT NULL,
            max_pause_duration REAL NOT NULL,
            total_pause_duration REAL NOT NULL,
            total_path_length REAL NOT NULL,
            tracking_duration REAL NOT NULL,
            point_count INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)
    conn.commit()

def validate_mouse_features(data: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Strictly validates the aggregate mouse feature payload.
    Ensures data type correctness, positive bounds, non-NaN/Inf, and reasonable ranges.
    Returns (is_valid, error_message).
    """
    if not isinstance(data, dict):
        return False, "Payload must be a JSON object."

    # Handle insufficient mouse movement samples gracefully
    if data.get('sample_available') is False:
        return True, "No sample available"

    for field in REQUIRED_MOUSE_FIELDS:
        if field not in data:
            return False, f"Missing required mouse feature: '{field}'."

        val = data[field]
        if isinstance(val, bool) or not isinstance(val, (int, float)):
            return False, f"Field '{field}' must be a numeric value."

        if math.isnan(val) or math.isinf(val):
            return False, f"Field '{field}' contains invalid numeric value (NaN or Infinity)."

    # Non-negative validation
    non_negative_fields = [
        'avg_velocity', 'std_velocity', 'min_velocity', 'max_velocity',
        'avg_acceleration', 'std_acceleration',
        'avg_curvature', 'std_curvature', 'total_direction_change',
        'jitter_score', 'pause_count', 'avg_pause_duration',
        'max_pause_duration', 'total_pause_duration',
        'total_path_length', 'tracking_duration'
    ]
    for field in non_negative_fields:
        if data[field] < 0:
            return False, f"Field '{field}' cannot be negative."

    point_count = data['point_count']
    if not isinstance(point_count, int) or point_count < MIN_POINT_COUNT:
        return False, f"Field 'point_count' must be an integer >= {MIN_POINT_COUNT}."

    if data['max_velocity'] > MAX_VELOCITY_PX_SEC:
        return False, f"Velocity exceeds maximum realistic threshold ({MAX_VELOCITY_PX_SEC} px/s)."

    if data['tracking_duration'] > MAX_TRACKING_DURATION_MS:
        return False, f"Tracking duration exceeds maximum threshold ({MAX_TRACKING_DURATION_MS} ms)."

    return True, ""

def save_mouse_features(user_id: int, features: Dict[str, Any]) -> Optional[int]:
    """
    Saves validated aggregate mouse features for a user into SQLite.
    Returns inserted row ID or None if no sample available.
    """
    is_valid, err = validate_mouse_features(features)
    if not is_valid:
        raise ValueError(err)

    if features.get('sample_available') is False:
        return None

    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        INSERT INTO mouse_features (
            user_id, avg_velocity, std_velocity, min_velocity, max_velocity,
            avg_acceleration, std_acceleration,
            avg_curvature, std_curvature, total_direction_change,
            jitter_score,
            pause_count, avg_pause_duration, max_pause_duration, total_pause_duration,
            total_path_length, tracking_duration, point_count
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        float(features['avg_velocity']),
        float(features['std_velocity']),
        float(features['min_velocity']),
        float(features['max_velocity']),
        float(features['avg_acceleration']),
        float(features['std_acceleration']),
        float(features['avg_curvature']),
        float(features['std_curvature']),
        float(features['total_direction_change']),
        float(features['jitter_score']),
        int(features['pause_count']),
        float(features['avg_pause_duration']),
        float(features['max_pause_duration']),
        float(features['total_pause_duration']),
        float(features['total_path_length']),
        float(features['tracking_duration']),
        int(features['point_count'])
    ))
    db.commit()
    return cursor.lastrowid

def get_user_mouse_features(user_id: int):
    """Retrieve all historical mouse feature samples for a user."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("""
        SELECT * FROM mouse_features WHERE user_id = ? ORDER BY created_at DESC
    """, (user_id,))
    rows = cursor.fetchall()
    return [dict(row) for row in rows]
