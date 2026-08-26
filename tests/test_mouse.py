import pytest
import os
import tempfile
import sqlite3
from app import create_app
from app.config import Config
from app.models.user import create_user
from app.models.mouse import get_user_mouse_features

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = 'test-secret-key'
        DATABASE_PATH = db_path

    app = create_app(TestConfig)

    with app.app_context():
        user = create_user('mouse_user', 'mouse@example.com', 'Password123')
        app.config['TEST_USER_ID'] = user['id']
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

@pytest.fixture
def authenticated_client(client):
    client.post('/login', data={
        'username': 'mouse_user',
        'password': 'Password123'
    })
    return client

def valid_mouse_payload():
    return {
        'avg_velocity': 450.2,
        'std_velocity': 120.5,
        'min_velocity': 50.0,
        'max_velocity': 850.0,
        'avg_acceleration': 1500.0,
        'std_acceleration': 350.0,
        'avg_curvature': 0.352,
        'std_curvature': 0.125,
        'total_direction_change': 4.25,
        'jitter_score': 0.082,
        'pause_count': 2,
        'avg_pause_duration': 140.0,
        'max_pause_duration': 180.0,
        'total_pause_duration': 280.0,
        'total_path_length': 620.5,
        'tracking_duration': 1450.0,
        'point_count': 25
    }

def test_mouse_endpoint_exists_unauthenticated(client):
    """1 & 2. Endpoint exists and unauthenticated requests are rejected (401)."""
    response = client.post('/api/behavior/mouse', json=valid_mouse_payload())
    assert response.status_code == 401

def test_authenticated_valid_mouse_payload(authenticated_client):
    """3. Authenticated valid mouse payload is accepted (201)."""
    response = authenticated_client.post('/api/behavior/mouse', json=valid_mouse_payload())
    assert response.status_code == 201
    assert response.is_json
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'sample_id' in data

def test_missing_fields_rejected(authenticated_client):
    """4. Missing required fields are rejected (400)."""
    payload = valid_mouse_payload()
    del payload['avg_velocity']
    response = authenticated_client.post('/api/behavior/mouse', json=payload)
    assert response.status_code == 400
    assert b"Missing required mouse feature" in response.data

def test_non_numeric_values_rejected(authenticated_client):
    """5. Non-numeric values are rejected (400)."""
    payload = valid_mouse_payload()
    payload['avg_velocity'] = "fast"
    response = authenticated_client.post('/api/behavior/mouse', json=payload)
    assert response.status_code == 400
    assert b"must be a numeric value" in response.data

def test_negative_values_rejected(authenticated_client):
    """6. Negative values are rejected (400)."""
    payload = valid_mouse_payload()
    payload['avg_velocity'] = -50.0
    response = authenticated_client.post('/api/behavior/mouse', json=payload)
    assert response.status_code == 400
    assert b"cannot be negative" in response.data

def test_nan_values_rejected(authenticated_client):
    """7. NaN values are rejected (400)."""
    payload = valid_mouse_payload()
    payload['avg_curvature'] = float('nan')
    response = authenticated_client.post('/api/behavior/mouse', json=payload)
    assert response.status_code == 400
    assert b"invalid numeric value" in response.data

def test_infinity_values_rejected(authenticated_client):
    """8. Infinity values are rejected (400)."""
    payload = valid_mouse_payload()
    payload['max_velocity'] = float('inf')
    response = authenticated_client.post('/api/behavior/mouse', json=payload)
    assert response.status_code == 400
    assert b"invalid numeric value" in response.data

def test_invalid_point_count_rejected(authenticated_client):
    """9. Invalid point count < 3 is rejected (400)."""
    payload = valid_mouse_payload()
    payload['point_count'] = 1
    response = authenticated_client.post('/api/behavior/mouse', json=payload)
    assert response.status_code == 400
    assert b"point_count" in response.data

def test_sample_stored_in_sqlite(authenticated_client, app):
    """10 & 11. Valid sample is stored in SQLite and belongs to authenticated user."""
    response = authenticated_client.post('/api/behavior/mouse', json=valid_mouse_payload())
    assert response.status_code == 201

    with app.app_context():
        user_id = app.config['TEST_USER_ID']
        samples = get_user_mouse_features(user_id)
        assert len(samples) >= 1
        sample = samples[0]
        assert sample['user_id'] == user_id
        assert sample['avg_velocity'] == 450.2
        assert sample['point_count'] == 25

def test_no_raw_trajectory_columns(app):
    """12. Confirm no raw trajectory (x, y, t array) columns exist in database schema."""
    with app.app_context():
        db = app.config['DATABASE_PATH']
        conn = sqlite3.connect(db)
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(mouse_features)")
        columns = [column[1] for column in cursor.fetchall()]
        conn.close()

        assert 'x' not in columns
        assert 'y' not in columns
        assert 'raw_trajectory' not in columns
        assert 'coordinates' not in columns

def test_low_movement_sample_graceful_handling(authenticated_client):
    """13. Minimal/no-movement sample is handled gracefully."""
    response = authenticated_client.post('/api/behavior/mouse', json={'sample_available': False})
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['sample_stored'] is False
