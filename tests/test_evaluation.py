import pytest
from app import create_app
from app.config import Config
from app.services.evaluation_service import (
    generate_synthetic_genuine_sample,
    generate_synthetic_bot_sample,
    generate_synthetic_slow_mimicry_sample,
    run_slow_mimicry_simulation,
    run_comprehensive_evaluation
)

class TestConfig(Config):
    TESTING = True
    DATABASE_PATH = ':memory:'

@pytest.fixture
def app():
    app = create_app(TestConfig)
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_synthetic_data_generators():
    ks_gen, ms_gen, ctx_gen = generate_synthetic_genuine_sample()
    assert ks_gen['avg_dwell_time'] > 50.0
    assert ms_gen['sample_available'] is True
    assert ctx_gen['device_status'] == 'known'

    ks_bot, ms_bot, ctx_bot = generate_synthetic_bot_sample()
    assert ks_bot['std_dwell_time'] < 1.0  # Robotic lack of variance
    assert ms_bot['avg_curvature'] < 0.001  # Robotic straight path
    assert ctx_bot['device_status'] == 'new'

    ks_mim, ms_mim, ctx_mim = generate_synthetic_slow_mimicry_sample(0, 15)
    assert 'avg_dwell_time' in ks_mim

def test_slow_mimicry_simulation_metrics():
    mimic_res = run_slow_mimicry_simulation(steps=10, max_drift_rate=0.10)
    assert mimic_res['total_steps'] == 10
    assert len(mimic_res['capped_scores']) == 10
    assert len(mimic_res['uncapped_scores']) == 10
    assert mimic_res['avg_capped_risk'] > 0.40

def test_comprehensive_evaluation_matrix():
    eval_res = run_comprehensive_evaluation(n_genuine=20, n_bot_attacks=20, n_mimicry_attacks=10)
    assert 'systems' in eval_res
    assert 'proposed' in eval_res['systems']
    assert 'password_captcha' in eval_res['systems']
    assert 'uncapped' in eval_res['systems']
    assert 'without_explanation' in eval_res['systems']

    prop = eval_res['systems']['proposed']
    assert prop['accuracy'] >= 90.0
    assert prop['explanation_accuracy'] > 0.0

def test_evaluation_web_routes(client):
    # GET dashboard
    resp = client.get('/evaluation')
    assert resp.status_code == 200
    assert b"Comparative Benchmark" in resp.data

    # POST run simulation API
    api_resp = client.post('/api/evaluation/run', json={
        'n_genuine': 15,
        'n_bot_attacks': 15,
        'n_mimicry_attacks': 10
    })
    assert api_resp.status_code == 200
    data = api_resp.get_json()
    assert 'systems' in data
    assert data['genuine_tested'] == 15

    # POST mimicry API
    mimic_resp = client.post('/api/evaluation/mimicry', json={
        'steps': 10,
        'max_drift_rate': 0.10
    })
    assert mimic_resp.status_code == 200
    mdata = mimic_resp.get_json()
    assert mdata['total_steps'] == 10
