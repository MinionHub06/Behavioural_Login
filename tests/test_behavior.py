import pytest
import os
import tempfile
import math
from app import create_app
from app.config import Config
from app.models.user import create_user
from app.models.keystroke import get_user_keystroke_features

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = 'test-secret-key'
        DATABASE_PATH = db_path

    app = create_app(TestConfig)

    with app.app_context():
        # Pre-create test user
        user = create_user('keystroke_user', 'keystroke@example.com', 'Password123')
        app.config['TEST_USER_ID'] = user['id']
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def authenticated_client(client, app):
    client.post('/login', data={
        'username': 'keystroke_user',
        'password': 'Password123'
    })
    return client

def valid_payload():
    return {
        'avg_dwell_time': 85.5,
        'std_dwell_time': 12.3,
        'min_dwell_time': 65.0,
        'max_dwell_time': 110.0,
        'avg_flight_time': 120.4,
        'std_flight_time': 25.1,
        'min_flight_time': 80.0,
        'max_flight_time': 160.0,
        'total_typing_duration': 1850.0,
        'typing_speed': 4.5,
        'typing_speed_variance': 0.72,
        'sample_count': 10
    }

def test_endpoint_exists_unauthenticated(client):
    """1 & 2. Behaviour endpoint exists and unauthenticated requests are rejected (401)."""
    response = client.post('/api/behavior/keystroke', json=valid_payload())
    assert response.status_code == 401
    assert response.is_json
    assert response.get_json()['status'] == 'error'

def test_authenticated_valid_payload_accepted(authenticated_client):
    """3. Authenticated valid behavioural payload is accepted (201)."""
    response = authenticated_client.post('/api/behavior/keystroke', json=valid_payload())
    assert response.status_code == 201
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'sample_id' in data

def test_missing_required_fields_rejected(authenticated_client):
    """4. Missing required fields are rejected (400)."""
    payload = valid_payload()
    del payload['avg_dwell_time']
    response = authenticated_client.post('/api/behavior/keystroke', json=payload)
    assert response.status_code == 400
    assert b"Missing required feature" in response.data

def test_non_numeric_values_rejected(authenticated_client):
    """5. Non-numeric values are rejected (400)."""
    payload = valid_payload()
    payload['avg_dwell_time'] = "eighty-five"
    response = authenticated_client.post('/api/behavior/keystroke', json=payload)
    assert response.status_code == 400
    assert b"must be a numeric value" in response.data

def test_negative_timing_values_rejected(authenticated_client):
    """6. Negative timing values are rejected (400)."""
    payload = valid_payload()
    payload['avg_dwell_time'] = -10.0
    response = authenticated_client.post('/api/behavior/keystroke', json=payload)
    assert response.status_code == 400
    assert b"cannot be negative" in response.data

def test_nan_infinity_values_rejected(authenticated_client):
    """7. NaN and Infinity values are rejected (400)."""
    payload = valid_payload()
    payload['std_dwell_time'] = float('nan')
    response = authenticated_client.post('/api/behavior/keystroke', json=payload)
    assert response.status_code == 400
    assert b"invalid numeric value" in response.data

def test_invalid_sample_count_rejected(authenticated_client):
    """8. Invalid sample count <= 0 is rejected (400)."""
    payload = valid_payload()
    payload['sample_count'] = 0
    response = authenticated_client.post('/api/behavior/keystroke', json=payload)
    assert response.status_code == 400
    assert b"sample_count" in response.data

def test_valid_feature_sample_stored_in_sqlite(authenticated_client, app):
    """9 & 10. Valid feature sample is stored in SQLite and associated with correct user ID."""
    response = authenticated_client.post('/api/behavior/keystroke', json=valid_payload())
    assert response.status_code == 201

    with app.app_context():
        user_id = app.config['TEST_USER_ID']
        samples = get_user_keystroke_features(user_id)
        assert len(samples) >= 1
        sample = samples[0]
        assert sample['user_id'] == user_id
        assert sample['avg_dwell_time'] == 85.5
        assert sample['sample_count'] == 10
