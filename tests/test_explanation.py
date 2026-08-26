import pytest
import os
import tempfile
import sqlite3
import json
from app import create_app
from app.config import Config
from app.models.user import create_user
from app.models.risk import save_risk_score, get_latest_user_risk_score
from app.risk_engine.explanation import (
    classify_severity,
    get_signal_status_text,
    generate_explanation
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
        user1 = create_user('exp_user1', 'e1@example.com', 'Password123')
        user2 = create_user('exp_user2', 'e2@example.com', 'Password123')
        app.config['USER1_ID'] = user1['id']
        app.config['USER2_ID'] = user2['id']
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_severity_boundaries():
    """8. Severity boundaries: normal (0-0.19), slightly (0.2-0.49), moderately (0.5-0.74), highly (0.75-1.0)."""
    assert classify_severity(0.0) == 'normal'
    assert classify_severity(0.19) == 'normal'
    assert classify_severity(0.20) == 'slightly unusual'
    assert classify_severity(0.49) == 'slightly unusual'
    assert classify_severity(0.50) == 'moderately unusual'
    assert classify_severity(0.74) == 'moderately unusual'
    assert classify_severity(0.75) == 'highly unusual'
    assert classify_severity(1.0) == 'highly unusual'

def test_contextual_signal_status_strings():
    """9-18. Validates status text for device, location, time, keystroke, and mouse."""
    # Device
    assert get_signal_status_text('device', 0.0, True) == "Known device"
    assert get_signal_status_text('device', 1.0, True) == "New device"
    assert get_signal_status_text('device', None, False) == "Device information unavailable"

    # Location
    assert get_signal_status_text('location', 0.0, True) == "Known location"
    assert get_signal_status_text('location', 1.0, True) == "New location"

    # Time
    assert get_signal_status_text('time', 0.0, True) == "Login time is within the user's usual pattern"
    assert get_signal_status_text('time', 1.0, True) == "Login time is outside the user's usual pattern"

    # Keystroke
    assert "close to the user's baseline" in get_signal_status_text('keystroke', 0.1, True)
    assert "differs substantially" in get_signal_status_text('keystroke', 0.8, True)

    # Mouse
    assert "close to the user's baseline" in get_signal_status_text('mouse', 0.1, True)
    assert "differs substantially" in get_signal_status_text('mouse', 0.8, True)

def test_contribution_and_relative_contribution_math():
    """1, 2, 3, 4, 5, 6, 7 & 19. Tests contribution, relative contribution, top 3 sorting, zero handling."""
    risk_result = {
        'risk_score': 0.67,
        'status': 'evaluated',
        'signals': {
            'keystroke': {'score': 0.72, 'available': True},
            'mouse': {'score': 0.31, 'available': True},
            'device': {'score': 1.0, 'available': True},
            'location': {'score': 0.0, 'available': True},
            'time': {'score': 1.0, 'available': True}
        }
    }
    weights = {'keystroke': 0.25, 'mouse': 0.25, 'device': 0.20, 'location': 0.15, 'time': 0.15}
    exp = generate_explanation(risk_result, weights)

    assert exp['overall_severity'] == 'moderately unusual'
    assert len(exp['top_contributors']) <= 3
    assert 'Device' in exp['top_contributors']

    # Check signal attributions
    signals_dict = {s['signal']: s for s in exp['signals']}
    # Device contribution = 1.0 * 0.20 = 0.20
    assert signals_dict['device']['contribution'] == 0.20
    # Keystroke contribution = 0.72 * 0.25 = 0.18
    assert signals_dict['keystroke']['contribution'] == 0.18

    # Sum of relative contributions for available signals equals 1.0
    rel_sum = sum(s['relative_contribution'] for s in exp['signals'] if s['available'])
    assert abs(rel_sum - 1.0) < 0.01

def test_zero_contribution_safety():
    """5. Zero total contribution is handled safely without division by zero."""
    risk_result = {
        'risk_score': 0.0,
        'status': 'evaluated',
        'signals': {
            'keystroke': {'score': 0.0, 'available': True},
            'mouse': {'score': 0.0, 'available': True},
            'device': {'score': 0.0, 'available': True},
            'location': {'score': 0.0, 'available': True},
            'time': {'score': 0.0, 'available': True}
        }
    }
    exp = generate_explanation(risk_result)
    assert exp['overall_severity'] == 'normal'
    assert exp['top_contributors'] == []
    for sig in exp['signals']:
        assert sig['relative_contribution'] == 0.0

def test_explanation_database_storage_and_user_isolation(client, app):
    """20, 21, 22 & 23. Explanation stored in SQLite and isolated per user."""
    client.post('/login', data={'username': 'exp_user1', 'password': 'Password123'})

    with app.app_context():
        user1_id = app.config['USER1_ID']
        user2_id = app.config['USER2_ID']
        rec1 = get_latest_user_risk_score(user1_id)
        rec2 = get_latest_user_risk_score(user2_id)

        assert rec1 is not None
        assert rec1['user_id'] == user1_id
        assert rec1['explanation'] is not None
        assert 'overall_severity' in rec1['explanation']
        assert rec2 is None

    # Check API returns explanation
    api_res = client.get('/api/risk/latest')
    assert api_res.status_code == 200
    json_data = api_res.get_json()
    assert json_data['risk_evaluation']['explanation'] is not None
