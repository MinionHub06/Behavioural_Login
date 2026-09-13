import pytest
import os
import tempfile
import json
from datetime import datetime
from app import create_app
from app.config import Config
from app.models.user import create_user
from app.services.otp_service import (
    generate_otp_for_user,
    verify_user_otp,
    get_active_otp
)

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()

    class TestConfig(Config):
        TESTING = True
        DATABASE_PATH = db_path
        SECRET_KEY = 'test-otp-secret'
        RISK_STEPUP_ENABLED = True
        OTP_EXPIRY_SECONDS = 300
        OTP_MAX_ATTEMPTS = 3

    app = create_app(TestConfig)
    with app.app_context():
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_otp_generation_and_verification(app):
    with app.app_context():
        user = create_user("otpuser", "otp@test.com", "Password123!")
        otp_code = generate_otp_for_user(user['id'])

        assert len(otp_code) == 6
        assert otp_code.isdigit()

        active = get_active_otp(user['id'])
        assert active is not None
        assert active['otp_code'] == otp_code

        # Successful verification
        is_valid, msg = verify_user_otp(user['id'], otp_code)
        assert is_valid is True
        assert "Identity verified successfully" in msg

        # Cannot reuse verified OTP
        is_valid_again, _ = verify_user_otp(user['id'], otp_code)
        assert is_valid_again is False

def test_otp_incorrect_attempt_and_lockout(app):
    with app.app_context():
        user = create_user("lockoutuser", "lockout@test.com", "Password123!")
        generate_otp_for_user(user['id'])

        # Attempt 1: wrong
        valid1, msg1 = verify_user_otp(user['id'], "000000", max_attempts=3)
        assert valid1 is False
        assert "2 attempt(s) remaining" in msg1

        # Attempt 2: wrong
        valid2, msg2 = verify_user_otp(user['id'], "111111", max_attempts=3)
        assert valid2 is False
        assert "1 attempt(s) remaining" in msg2

        # Attempt 3: wrong
        valid3, msg3 = verify_user_otp(user['id'], "222222", max_attempts=3)
        assert valid3 is False
        assert "Maximum attempts reached" in msg3

        # Attempt 4: locked out
        valid4, msg4 = verify_user_otp(user['id'], "333333", max_attempts=3)
        assert valid4 is False
        assert "Too many failed attempts" in msg4

def test_otp_expiration(app):
    with app.app_context():
        user = create_user("expireduser", "exp@test.com", "Password123!")
        # Expired in past
        otp = generate_otp_for_user(user['id'], expiry_seconds=-1)
        is_valid, msg = verify_user_otp(user['id'], otp)
        assert is_valid is False
        assert "expired" in msg

def test_step_up_login_flow_redirects_and_verifies(client, app):
    with app.app_context():
        user = create_user("anomaloususer", "anom@test.com", "ValidPass123!")
        # Establish baseline first
        from app.models.keystroke import save_keystroke_features
        from app.models.mouse import save_mouse_features
        from app.models.context import save_context_features
        from app.services.baseline_service import create_or_update_user_baseline

        normal_ks = {
            'avg_dwell_time': 100.0, 'std_dwell_time': 10.0,
            'min_dwell_time': 80.0, 'max_dwell_time': 120.0,
            'avg_flight_time': 120.0, 'std_flight_time': 15.0,
            'min_flight_time': 90.0, 'max_flight_time': 150.0,
            'total_typing_duration': 2000.0, 'typing_speed': 50.0,
            'typing_speed_variance': 20.0, 'sample_count': 10
        }
        normal_ms = {
            'sample_available': True, 'avg_velocity': 300.0, 'std_velocity': 50.0,
            'min_velocity': 100.0, 'max_velocity': 500.0,
            'avg_acceleration': 600.0, 'std_acceleration': 100.0, 'avg_curvature': 0.05,
            'std_curvature': 0.01, 'total_direction_change': 3.0, 'jitter_score': 0.03,
            'pause_count': 2, 'avg_pause_duration': 150.0, 'max_pause_duration': 200.0,
            'total_pause_duration': 300.0, 'total_path_length': 800.0, 'tracking_duration': 2000.0,
            'point_count': 50
        }
        normal_ctx = {
            'user_id': user['id'], 'device_id': 'known-dev-1',
            'ip_address': '127.0.0.1', 'location': 'LOCAL',
            'login_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'login_hour': 14, 'device_status': 'known',
            'location_status': 'known', 'time_status': 'usual',
            'new_device': False, 'new_location': False, 'unusual_time': False
        }
        for _ in range(3):
            save_keystroke_features(user['id'], normal_ks)
            save_mouse_features(user['id'], normal_ms)
            save_context_features(normal_ctx)
        create_or_update_user_baseline(user['id'])

    # Perform anomalous login attempt with abnormal features -> risk > 0.50
    anomalous_ks = {
        'avg_dwell_time': 500.0, 'std_dwell_time': 80.0,
        'min_dwell_time': 400.0, 'max_dwell_time': 600.0,
        'avg_flight_time': 600.0, 'std_flight_time': 90.0,
        'min_flight_time': 500.0, 'max_flight_time': 700.0,
        'total_typing_duration': 8000.0, 'typing_speed': 10.0,
        'typing_speed_variance': 100.0, 'sample_count': 10
    }
    response = client.post('/login', data={
        'username': 'anomaloususer',
        'password': 'ValidPass123!',
        'keystroke_data': json.dumps(anomalous_ks)
    }, follow_redirects=False)

    # Should redirect to /verify-otp because of elevated risk
    assert response.status_code == 302
    assert '/verify-otp' in response.headers['Location']

    # Follow redirect to verify-otp page
    page = client.get('/verify-otp')
    assert page.status_code == 200
    assert b"Step-Up Verification" in page.data

    with client.session_transaction() as sess:
        demo_otp = sess.get('demo_otp')
        assert demo_otp is not None

    # Submit wrong OTP -> 400 Bad Request
    wrong_resp = client.post('/verify-otp', data={'otp_code': '000000'}, follow_redirects=True)
    assert wrong_resp.status_code == 400
    assert b"Invalid verification code" in wrong_resp.data

    # Submit correct OTP -> 200 on /dashboard
    good_resp = client.post('/verify-otp', data={'otp_code': demo_otp}, follow_redirects=True)
    assert good_resp.status_code == 200
    assert b"Welcome, anomaloususer" in good_resp.data
