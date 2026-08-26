import pytest
from app import create_app
from app.config import Config

class TestConfig(Config):
    TESTING = True
    DATABASE_PATH = ':memory:'

@pytest.fixture
def app():
    """Create and configure a new app instance for each test."""
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()

def test_app_creation(app):
    """Test that application instance is created successfully."""
    assert app is not None
    assert app.config['TESTING'] is True

def test_home_page(client):
    """Test GET / returns HTTP 200 and expected HTML content."""
    response = client.get('/')
    assert response.status_code == 200
    html_content = response.data.decode('utf-8')
    assert "Behavioural Login Verification System" in html_content
    assert "Cyber Security Project" in html_content
    assert "System Status: Running" in html_content
    assert "Behavioural authentication modules will be integrated here." in html_content

def test_health_check(client):
    """Test GET /health returns HTTP 200 and JSON with status ok."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.is_json
    data = response.get_json()
    assert data.get('status') == 'ok'
    assert data.get('service') == 'behavioural-login-verification'

def test_404_error(client):
    """Test 404 error handler returns JSON with 404 status code."""
    response = client.get('/non-existent-route')
    assert response.status_code == 404
    assert response.is_json
    data = response.get_json()
    assert data.get('status_code') == 404
    assert 'error' in data
