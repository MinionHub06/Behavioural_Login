import pytest
import os
import tempfile
from app import create_app
from app.config import Config
from app.models.user import get_user_by_username, verify_user_password

@pytest.fixture
def app():
    db_fd, db_path = tempfile.mkstemp()
    
    class TestConfig(Config):
        TESTING = True
        SECRET_KEY = 'test-secret-key'
        DATABASE_PATH = db_path

    app = create_app(TestConfig)
    
    with app.app_context():
        yield app

    os.close(db_fd)
    if os.path.exists(db_path):
        os.unlink(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_registration_page_loads(client):
    """1. Registration page loads successfully."""
    response = client.get('/register')
    assert response.status_code == 200
    assert b"Create Account" in response.data

def test_login_page_loads(client):
    """2. Login page loads successfully."""
    response = client.get('/login')
    assert response.status_code == 200
    assert b"Account Portal" in response.data

def test_user_registration(client, app):
    """3. User can register with valid credentials."""
    response = client.post('/register', data={
        'username': 'alice',
        'email': 'alice@example.com',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration successful! Please log in." in response.data

def test_password_stored_as_hash(client, app):
    """4. Password is stored as a hash and NOT plaintext."""
    client.post('/register', data={
        'username': 'bob',
        'email': 'bob@example.com',
        'password': 'SecretPassword123',
        'confirm_password': 'SecretPassword123'
    })
    
    with app.app_context():
        user = get_user_by_username('bob')
        assert user is not None
        assert user['password_hash'] != 'SecretPassword123'
        assert user['password_hash'].startswith(('scrypt:', 'pbkdf2:'))
        assert verify_user_password(user, 'SecretPassword123') is True
        assert verify_user_password(user, 'WrongPassword') is False

def test_duplicate_username_rejected(client):
    """5. Duplicate username registration is rejected."""
    client.post('/register', data={
        'username': 'charlie',
        'email': 'charlie1@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    
    response = client.post('/register', data={
        'username': 'charlie',
        'email': 'charlie2@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    assert response.status_code == 400
    assert b"Username is already taken." in response.data

def test_duplicate_email_rejected(client):
    """6. Duplicate email registration is rejected."""
    client.post('/register', data={
        'username': 'dave1',
        'email': 'dave@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    
    response = client.post('/register', data={
        'username': 'dave2',
        'email': 'dave@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    assert response.status_code == 400
    assert b"Email is already registered." in response.data

def test_password_mismatch_rejected(client):
    """7. Registration with password mismatch is rejected."""
    response = client.post('/register', data={
        'username': 'eve',
        'email': 'eve@example.com',
        'password': 'Password123',
        'confirm_password': 'DifferentPassword456'
    })
    assert response.status_code == 400
    assert b"Passwords do not match." in response.data

def test_valid_credentials_login(client):
    """8. Valid credentials successfully log in and redirect to /dashboard."""
    client.post('/register', data={
        'username': 'frank',
        'email': 'frank@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })

    response = client.post('/login', data={
        'username': 'frank',
        'password': 'Password123'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b"Welcome, frank" in response.data
    assert b"Authentication successful." in response.data

def test_invalid_credentials_rejected(client):
    """9. Invalid credentials are rejected with a generic error message."""
    client.post('/register', data={
        'username': 'grace',
        'email': 'grace@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })

    response = client.post('/login', data={
        'username': 'grace',
        'password': 'WrongPassword'
    })
    assert response.status_code == 401
    assert b"Invalid username or password." in response.data

def test_authenticated_user_access_dashboard(client):
    """10. Authenticated user can access /dashboard."""
    client.post('/register', data={
        'username': 'helen',
        'email': 'helen@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    client.post('/login', data={
        'username': 'helen',
        'password': 'Password123'
    })

    response = client.get('/dashboard')
    assert response.status_code == 200
    assert b"Welcome, helen" in response.data

def test_unauthenticated_user_cannot_access_dashboard(client):
    """11. Unauthenticated user cannot access /dashboard and is redirected to /login."""
    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']

def test_logout_works(client):
    """12. Logout removes user session and redirects to /login."""
    client.post('/register', data={
        'username': 'ian',
        'email': 'ian@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    client.post('/login', data={
        'username': 'ian',
        'password': 'Password123'
    })

    response = client.get('/logout', follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been logged out successfully." in response.data

def test_access_dashboard_after_logout(client):
    """13. Accessing /dashboard after logout redirects to /login."""
    client.post('/register', data={
        'username': 'jack',
        'email': 'jack@example.com',
        'password': 'Password123',
        'confirm_password': 'Password123'
    })
    client.post('/login', data={
        'username': 'jack',
        'password': 'Password123'
    })
    client.get('/logout')

    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert '/login' in response.headers['Location']
