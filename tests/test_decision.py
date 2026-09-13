import pytest
from app.risk_engine.decision import (
    evaluate_risk_decision,
    ACTION_ALLOW,
    ACTION_STEP_UP_OTP,
    ACTION_ALLOW_INITIAL
)

def test_initial_baseline_allows_without_otp():
    risk_eval = {
        'risk_score': None,
        'status': 'insufficient_baseline',
        'explanation': {'overall_severity': 'normal', 'summary': 'Insufficient baseline.'}
    }
    decision = evaluate_risk_decision(risk_eval, threshold_high=0.50)
    assert decision['action'] == ACTION_ALLOW_INITIAL
    assert decision['requires_otp'] is False
    assert "baseline profile is being established" in decision['reason']

def test_low_risk_allows_seamless_access():
    risk_eval = {
        'risk_score': 0.15,
        'status': 'evaluated',
        'explanation': {
            'overall_severity': 'normal',
            'summary': 'Login behaviour matches established pattern.',
            'top_contributors': []
        }
    }
    decision = evaluate_risk_decision(risk_eval, threshold_high=0.50)
    assert decision['action'] == ACTION_ALLOW
    assert decision['requires_otp'] is False
    assert decision['risk_score'] == 0.15

def test_high_risk_triggers_step_up_otp():
    risk_eval = {
        'risk_score': 0.72,
        'status': 'evaluated',
        'explanation': {
            'overall_severity': 'moderately unusual',
            'summary': 'Login behaviour differs moderately due to device, typing rhythm.',
            'top_contributors': ['Device', 'Keystroke behaviour']
        }
    }
    decision = evaluate_risk_decision(risk_eval, threshold_high=0.50)
    assert decision['action'] == ACTION_STEP_UP_OTP
    assert decision['requires_otp'] is True
    assert decision['risk_score'] == 0.72
    assert "Device" in decision['reason']
    assert "Keystroke behaviour" in decision['reason']

def test_disabled_stepup_allows_access():
    risk_eval = {
        'risk_score': 0.85,
        'status': 'evaluated',
        'explanation': {'overall_severity': 'highly unusual', 'top_contributors': ['Device']}
    }
    decision = evaluate_risk_decision(risk_eval, threshold_high=0.50, stepup_enabled=False)
    assert decision['action'] == ACTION_ALLOW
    assert decision['requires_otp'] is False
