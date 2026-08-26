import pytest
import os
import tempfile
from datetime import datetime, timezone, timedelta
from app import create_app
from app.config import Config
from app.models.user import create_user
from app.models.context import save_context_features, get_user_context_features
from app.services.context_service import (
    get_client_ip, get_location_from_ip, generate_device_id,
    is_hour_in_usual_range, evaluate_context_signals
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
        user = create_user('context_user', 'context@example.com', 'Password123')
        app.config['TEST_USER_ID'] = user['id']
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_client_ip_and_private_handling(app):
    """1 & 2. Client IP is retrieved safely and local/private IP handled cleanly."""
    with app.test_request_context('/', environ_base={'REMOTE_ADDR': '127.0.0.1'}):
        from flask import request
        ip = get_client_ip(request)
        assert ip == '127.0.0.1'

def test_location_abstraction_local_unknown(app):
    """3. Unknown/local location represented as LOCAL/UNKNOWN without false geolocation claims."""
    assert get_location_from_ip('127.0.0.1') == 'LOCAL'
    assert get_location_from_ip('10.0.0.1') == 'LOCAL'
    assert get_location_from_ip('192.168.1.50') == 'LOCAL'

def test_first_login_context_evaluation(app):
    """4. First login results in neutral unknown status flags without false positive warnings."""
    user_id = app.config['TEST_USER_ID']
    now = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)
    res = evaluate_context_signals(
        user_id=user_id,
        current_device_id='device_hash_1',
        current_ip='127.0.0.1',
        current_location='LOCAL',
        current_login_time=now,
        historical_samples=[]
    )
    assert res['device_status'] == 'unknown'
    assert res['location_status'] == 'unknown'
    assert res['time_status'] == 'unknown'
    assert res['new_device'] is False
    assert res['new_location'] is False
    assert res['unusual_time'] is False

def test_known_vs_new_device_recognition(app):
    """5 & 6. Known device recognized; new device flagged when device ID changes."""
    user_id = app.config['TEST_USER_ID']
    now = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)
    history = [{
        'device_id': 'device_hash_1',
        'location': 'LOCAL',
        'login_hour': 14
    }]

    # Same device
    known_eval = evaluate_context_signals(user_id, 'device_hash_1', '127.0.0.1', 'LOCAL', now, history)
    assert known_eval['device_status'] == 'known'
    assert known_eval['new_device'] is False

    # New device
    new_eval = evaluate_context_signals(user_id, 'device_hash_2', '127.0.0.1', 'LOCAL', now, history)
    assert new_eval['device_status'] == 'new'
    assert new_eval['new_device'] is True

def test_location_status_recognition(app):
    """7, 8 & 9. Known location recognized; new location flagged only when real location differs; UNKNOWN does not trigger new_location."""
    user_id = app.config['TEST_USER_ID']
    now = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)

    # UNKNOWN / LOCAL does not trigger new_location
    history_local = [{'device_id': 'd1', 'location': 'LOCAL', 'login_hour': 14}]
    eval_local = evaluate_context_signals(user_id, 'd1', '127.0.0.1', 'LOCAL', now, history_local)
    assert eval_local['location_status'] == 'unknown'
    assert eval_local['new_location'] is False

    # Known public location
    history_public = [{'device_id': 'd1', 'location': 'IN/MH', 'login_hour': 14}]

    # Same public location
    eval_same_loc = evaluate_context_signals(user_id, 'd1', '203.0.113.5', 'IN/MH', now, history_public)
    assert eval_same_loc['location_status'] == 'known'
    assert eval_same_loc['new_location'] is False

    # New public location
    eval_new_loc = evaluate_context_signals(user_id, 'd1', '198.51.100.2', 'US/CA', now, history_public)
    assert eval_new_loc['location_status'] == 'new'
    assert eval_new_loc['new_location'] is True

def test_usual_vs_unusual_time_evaluation(app):
    """10 & 11. Login time evaluated against historical range (handling midnight circular wraparound)."""
    user_id = app.config['TEST_USER_ID']
    # 3 historical samples around midnight (23:00, 00:00, 01:00)
    history = [
        {'device_id': 'd1', 'location': 'LOCAL', 'login_hour': 23},
        {'device_id': 'd1', 'location': 'LOCAL', 'login_hour': 0},
        {'device_id': 'd1', 'location': 'LOCAL', 'login_hour': 1}
    ]

    # Usual time: 02:00 (within 2-hour window of 01:00 and 00:00)
    now_usual = datetime(2026, 8, 25, 2, 0, tzinfo=timezone.utc)
    eval_usual = evaluate_context_signals(user_id, 'd1', '127.0.0.1', 'LOCAL', now_usual, history)
    assert eval_usual['time_status'] == 'usual'
    assert eval_usual['unusual_time'] is False

    # Unusual time: 14:00 (far from 23, 0, 1)
    now_unusual = datetime(2026, 8, 25, 14, 0, tzinfo=timezone.utc)
    eval_unusual = evaluate_context_signals(user_id, 'd1', '127.0.0.1', 'LOCAL', now_unusual, history)
    assert eval_unusual['time_status'] == 'unusual'
    assert eval_unusual['unusual_time'] is True

def test_context_stored_on_successful_login(client, app):
    """12 & 13. Context record is automatically stored in SQLite upon login and belongs to user ID."""
    login_res = client.post('/login', data={
        'username': 'context_user',
        'password': 'Password123'
    })
    assert login_res.status_code == 302 # Redirect to dashboard

    with app.app_context():
        user_id = app.config['TEST_USER_ID']
        records = get_user_context_features(user_id)
        assert len(records) >= 1
        rec = records[0]
        assert rec['user_id'] == user_id
        assert 'device_id' in rec
        assert rec['ip_address'] == '127.0.0.1'
        assert rec['location'] == 'LOCAL'
