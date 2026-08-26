import pytest
import os
import tempfile
import sqlite3
import math
from app import create_app
from app.config import Config
from app.models.user import create_user
from app.models.keystroke import save_keystroke_features
from app.models.mouse import save_mouse_features
from app.models.context import save_context_features
from app.models.baseline import get_user_baseline_record
from app.services.baseline_service import (
    weighted_mean,
    calculate_keystroke_baseline,
    calculate_mouse_baseline,
    calculate_context_baseline,
    create_or_update_user_baseline,
    get_user_baseline
)

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = 'test-secret-key'
        DATABASE_PATH = db_path
        BASELINE_DECAY_FACTOR = 0.8

    app = create_app(TestConfig)

    with app.app_context():
        user1 = create_user('baseline_user1', 'b1@example.com', 'Password123')
        user2 = create_user('baseline_user2', 'b2@example.com', 'Password123')
        app.config['USER1_ID'] = user1['id']
        app.config['USER2_ID'] = user2['id']
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_baseline_table_creation(app):
    """1. Baseline table is created in SQLite database."""
    with app.app_context():
        db = app.config['DATABASE_PATH']
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='behavioural_baselines'")
        table = cursor.fetchone()
        conn.close()
        assert table is not None

def test_weighted_mean_math():
    """5, 7, 8, 9 & 10. Weighted mean is mathematically correct, handles missing/NaN/Inf/non-numeric."""
    vals = [10.0, 20.0, 30.0]
    weights = [1.0, 0.8, 0.64]
    # Sum(w*v) = 10*1 + 20*0.8 + 30*0.64 = 10 + 16 + 19.2 = 45.2
    # Sum(w) = 1 + 0.8 + 0.64 = 2.44
    # Mean = 45.2 / 2.44 = 18.52459... -> 18.52
    expected = round(45.2 / 2.44, 2)
    assert weighted_mean(vals, weights) == expected

    # Ignores NaN, Inf, None, strings
    dirty_vals = [10.0, float('nan'), float('inf'), None, "invalid", 20.0]
    dirty_weights = [1.0, 0.8, 0.64, 0.5, 0.4, 0.8]
    # Valid: 10*1.0 + 20*0.8 = 26.0; sum(w) = 1.8 -> 26/1.8 = 14.44
    assert weighted_mean(dirty_vals, dirty_weights) == round(26.0 / 1.8, 2)

def test_recency_weighting_decay_effect():
    """6. Recent samples receive greater weight than older samples."""
    # Old sample: typing speed = 3.0 (age = 2, weight = 0.64)
    # Recent sample: typing speed = 9.0 (age = 0, weight = 1.0)
    samples = [
        {'typing_speed': 9.0}, # Newest (idx 0, weight 1.0)
        {'typing_speed': 6.0}, # Middle (idx 1, weight 0.8)
        {'typing_speed': 3.0}  # Oldest (idx 2, weight 0.64)
    ]
    res = calculate_keystroke_baseline(samples, decay_factor=0.8)

    # Simple average would be (9 + 6 + 3) / 3 = 6.0
    # Weighted average = (9*1 + 6*0.8 + 3*0.64) / (1 + 0.8 + 0.64) = (9 + 4.8 + 1.92) / 2.44 = 15.72 / 2.44 = 6.44
    assert res['typing_speed'] == 6.44
    assert res['typing_speed'] > 6.0 # Pulled stronger toward recent value 9.0!

def test_baseline_status_states(app):
    """2, 3, 4 & 20. Baseline status is insufficient_data (0), initial (1), established (2+)."""
    user_id = app.config['USER1_ID']

    with app.app_context():
        # 0 samples
        bl0 = create_or_update_user_baseline(user_id)
        assert bl0['status'] == 'insufficient_data'
        assert bl0['sample_count'] == 0

        # 1 sample
        save_keystroke_features(user_id, {
            'avg_dwell_time': 80.0, 'std_dwell_time': 10.0, 'min_dwell_time': 60.0, 'max_dwell_time': 100.0,
            'avg_flight_time': 110.0, 'std_flight_time': 20.0, 'min_flight_time': 80.0, 'max_flight_time': 150.0,
            'total_typing_duration': 1500.0, 'typing_speed': 5.0, 'typing_speed_variance': 0.5, 'sample_count': 8
        })
        bl1 = create_or_update_user_baseline(user_id)
        assert bl1['status'] == 'initial'
        assert bl1['sample_count'] == 1

        # 2+ samples
        save_keystroke_features(user_id, {
            'avg_dwell_time': 85.0, 'std_dwell_time': 12.0, 'min_dwell_time': 65.0, 'max_dwell_time': 105.0,
            'avg_flight_time': 115.0, 'std_flight_time': 22.0, 'min_flight_time': 85.0, 'max_flight_time': 155.0,
            'total_typing_duration': 1600.0, 'typing_speed': 4.8, 'typing_speed_variance': 0.45, 'sample_count': 8
        })
        bl2 = create_or_update_user_baseline(user_id)
        assert bl2['status'] == 'established'
        assert bl2['sample_count'] == 2

def test_context_baseline_collection():
    """13, 14, 15 & 16. Context baseline collects known devices/locations, excludes LOCAL/UNKNOWN, computes hour distribution."""
    context_samples = [
        {'device_id': 'dev_hash_a', 'location': 'IN/MH', 'login_hour': 18},
        {'device_id': 'dev_hash_a', 'location': 'LOCAL', 'login_hour': 18},
        {'device_id': 'dev_hash_b', 'location': 'US/CA', 'login_hour': 20},
        {'device_id': 'unknown', 'location': 'UNKNOWN', 'login_hour': 18}
    ]
    res = calculate_context_baseline(context_samples)

    assert res['known_devices'] == ['dev_hash_a', 'dev_hash_b']
    assert res['known_locations'] == ['IN/MH', 'US/CA']
    assert 'LOCAL' not in res['known_locations']
    assert 'UNKNOWN' not in res['known_locations']
    assert res['login_hour_distribution'] == {'18': 3, '20': 1}

def test_baseline_version_increment(app):
    """19. Baseline version starts at 1 and increments on each update."""
    user_id = app.config['USER1_ID']

    with app.app_context():
        save_keystroke_features(user_id, {
            'avg_dwell_time': 80.0, 'std_dwell_time': 10.0, 'min_dwell_time': 60.0, 'max_dwell_time': 100.0,
            'avg_flight_time': 110.0, 'std_flight_time': 20.0, 'min_flight_time': 80.0, 'max_flight_time': 150.0,
            'total_typing_duration': 1500.0, 'typing_speed': 5.0, 'typing_speed_variance': 0.5, 'sample_count': 8
        })
        b1 = create_or_update_user_baseline(user_id)
        assert b1['baseline_version'] == 1

        b2 = create_or_update_user_baseline(user_id)
        assert b2['baseline_version'] == 2

def test_user_isolation(client, app):
    """17, 18. User A cannot access or overwrite User B's baseline via authenticated session."""
    user1_id = app.config['USER1_ID']
    user2_id = app.config['USER2_ID']

    with app.app_context():
        create_or_update_user_baseline(user1_id)
        create_or_update_user_baseline(user2_id)

    # Login as User 1
    client.post('/login', data={'username': 'baseline_user1', 'password': 'Password123'})
    res = client.get('/api/baseline')
    assert res.status_code == 200
    data = res.get_json()
    assert data['baseline']['user_id'] == user1_id
    assert data['baseline']['user_id'] != user2_id
