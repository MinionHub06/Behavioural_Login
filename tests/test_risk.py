import pytest
import os
import tempfile
import sqlite3
import math
from app import create_app
from app.config import Config
from app.models.user import create_user
from app.models.risk import save_risk_score, get_latest_user_risk_score
from app.risk_engine.scoring import (
    normalized_feature_anomaly,
    calculate_keystroke_anomaly,
    calculate_mouse_anomaly,
    calculate_device_anomaly,
    calculate_location_anomaly,
    calculate_time_anomaly,
    validate_weights,
    calculate_combined_risk,
    evaluate_login_risk
)

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = 'test-secret-key'
        DATABASE_PATH = db_path

    app = create_app(TestConfig)

    with app.app_context():
        user1 = create_user('risk_user1', 'r1@example.com', 'Password123')
        user2 = create_user('risk_user2', 'r2@example.com', 'Password123')
        app.config['USER1_ID'] = user1['id']
        app.config['USER2_ID'] = user2['id']
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_numerical_feature_anomaly_math():
    """1, 2, 3, 4, 5, 6 & 7. Validates feature anomaly math, clamping, and handling of dirty values."""
    # Identical value -> 0.0
    assert normalized_feature_anomaly(100.0, 100.0, 10.0) == 0.0

    # Small deviation (diff=3.0, std=10.0, z=0.3 -> z/3 = 0.1)
    assert normalized_feature_anomaly(103.0, 100.0, 10.0) == 0.1

    # Large deviation (diff=60.0, std=10.0, z=6.0 -> z/3 = 2.0 -> clamped 1.0)
    assert normalized_feature_anomaly(160.0, 100.0, 10.0) == 1.0

    # Zero / near-zero std handling
    assert normalized_feature_anomaly(10.0, 10.0, 0.0) == 0.0

    # NaN / Inf / None handling
    assert normalized_feature_anomaly(float('nan'), 100.0, 10.0) is None
    assert normalized_feature_anomaly(float('inf'), 100.0, 10.0) is None
    assert normalized_feature_anomaly(None, 100.0, 10.0) is None

def test_keystroke_and_mouse_anomaly_scoring():
    """8 & 9. Keystroke and mouse anomaly scores calculated correctly."""
    cur_ks = {'avg_dwell_time': 80.0, 'avg_flight_time': 110.0, 'typing_speed': 5.0}
    base_ks = {'avg_dwell_time': 80.0, 'avg_flight_time': 110.0, 'typing_speed': 5.0}
    ks_res = calculate_keystroke_anomaly(cur_ks, base_ks)
    assert ks_res['available'] is True
    assert ks_res['score'] == 0.0

    cur_ms = {'avg_velocity': 800.0, 'avg_acceleration': 2500.0}
    base_ms = {'avg_velocity': 400.0, 'avg_acceleration': 1200.0}
    ms_res = calculate_mouse_anomaly(cur_ms, base_ms)
    assert ms_res['available'] is True
    assert ms_res['score'] > 0.0

def test_contextual_anomaly_scores():
    """10-18. Device, location, and time contextual anomaly evaluation rules."""
    # Device
    assert calculate_device_anomaly({'device_status': 'known'})['score'] == 0.0
    assert calculate_device_anomaly({'device_status': 'new'})['score'] == 1.0
    assert calculate_device_anomaly({'device_status': 'unknown'})['score'] == 0.0

    # Location
    assert calculate_location_anomaly({'location_status': 'known'})['score'] == 0.0
    assert calculate_location_anomaly({'location_status': 'new'})['score'] == 1.0
    assert calculate_location_anomaly({'location_status': 'unknown'})['score'] == 0.0

    # Time
    assert calculate_time_anomaly({'time_status': 'usual'})['score'] == 0.0
    assert calculate_time_anomaly({'time_status': 'unusual'})['score'] == 1.0
    assert calculate_time_anomaly({'time_status': 'unknown'})['score'] == 0.0

def test_weight_validation_and_missing_signal_redistribution():
    """19, 20 & 21. Weight validation and proportional redistribution for missing signals."""
    weights = {'keystroke': 0.25, 'mouse': 0.25, 'device': 0.20, 'location': 0.15, 'time': 0.15}
    assert validate_weights(weights) is True

    # All signals present: device = 1.0, others = 0.0 -> risk = 0.20 * 1.0 = 0.20
    signals = {
        'keystroke': {'score': 0.0, 'available': True},
        'mouse': {'score': 0.0, 'available': True},
        'device': {'score': 1.0, 'available': True},
        'location': {'score': 0.0, 'available': True},
        'time': {'score': 0.0, 'available': True}
    }
    res = calculate_combined_risk(signals, weights)
    assert res['risk_score'] == 0.20

    # Mouse unavailable: available weights = 0.75 -> device norm_weight = 0.20 / 0.75 = 0.2667
    signals_no_mouse = {
        'keystroke': {'score': 0.0, 'available': True},
        'mouse': {'score': 0.0, 'available': False},
        'device': {'score': 1.0, 'available': True},
        'location': {'score': 0.0, 'available': True},
        'time': {'score': 0.0, 'available': True}
    }
    res_no_mouse = calculate_combined_risk(signals_no_mouse, weights)
    assert res_no_mouse['risk_score'] == 0.2667

def test_insufficient_baseline_handling(app):
    """22. Insufficient baseline handled gracefully without false alerts."""
    user_id = app.config['USER1_ID']
    with app.app_context():
        res = evaluate_login_risk(user_id=user_id, context_eval={'device_status': 'unknown'})
        assert res['status'] == 'insufficient_baseline'
        assert res['risk_score'] is None

def test_risk_score_storage_and_user_isolation(client, app):
    """23 & 24. Risk score saved in SQLite database and isolated per user session."""
    login_res = client.post('/login', data={'username': 'risk_user1', 'password': 'Password123'})
    assert login_res.status_code == 302

    with app.app_context():
        user1_id = app.config['USER1_ID']
        user2_id = app.config['USER2_ID']
        rec1 = get_latest_user_risk_score(user1_id)
        rec2 = get_latest_user_risk_score(user2_id)
        assert rec1 is not None
        assert rec1['user_id'] == user1_id
        assert rec2 is None

    # Test debug endpoint
    api_res = client.get('/api/risk/latest')
    assert api_res.status_code == 200
    json_data = api_res.get_json()
    assert json_data['status'] == 'success'
    assert json_data['risk_evaluation']['user_id'] == user1_id
