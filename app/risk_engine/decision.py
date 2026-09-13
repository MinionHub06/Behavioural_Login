from typing import Dict, Any, Optional
from app.config import Config

# Action constants
ACTION_ALLOW = "ALLOW"
ACTION_STEP_UP_OTP = "STEP_UP_OTP"
ACTION_ALLOW_INITIAL = "ALLOW_INITIAL"
ACTION_BLOCK = "BLOCK"

def evaluate_risk_decision(
    risk_eval: Optional[Dict[str, Any]],
    threshold_low: float = Config.RISK_THRESHOLD_LOW,
    threshold_high: float = Config.RISK_THRESHOLD_HIGH,
    stepup_enabled: bool = Config.RISK_STEPUP_ENABLED
) -> Dict[str, Any]:
    """
    Evaluates risk score against security thresholds to determine authentication action.
    
    Decision Rules:
    1. If baseline is insufficient / status is 'insufficient_baseline' -> ALLOW_INITIAL (First logins pass without friction).
    2. If risk_score is None or unevaluated -> ALLOW_INITIAL.
    3. If stepup_enabled is False -> ALLOW.
    4. If risk_score < threshold_high -> ALLOW (Normal / low risk, seamless login).
    5. If risk_score >= threshold_high -> STEP_UP_OTP (Elevated / high risk triggers step-up verification).
    """
    if not risk_eval:
        return {
            'action': ACTION_ALLOW_INITIAL,
            'requires_otp': False,
            'reason': 'No risk evaluation data available. Defaulting to standard access.',
            'risk_score': None,
            'severity': 'unknown',
            'explanation_summary': 'Initial profile establishment.',
            'top_contributors': []
        }

    status = risk_eval.get('status', 'unevaluated')
    risk_score = risk_eval.get('risk_score')
    explanation = risk_eval.get('explanation') or {}
    severity = explanation.get('overall_severity', 'unknown')
    summary = explanation.get('summary', 'Risk evaluated.')
    top_contributors = explanation.get('top_contributors', [])

    if status in ('insufficient_baseline', 'insufficient_data') or risk_score is None:
        return {
            'action': ACTION_ALLOW_INITIAL,
            'requires_otp': False,
            'reason': 'Initial login: baseline profile is being established.',
            'risk_score': None,
            'severity': 'normal',
            'explanation_summary': 'Establishing baseline profile.',
            'top_contributors': []
        }

    if not stepup_enabled:
        return {
            'action': ACTION_ALLOW,
            'requires_otp': False,
            'reason': 'Step-up verification is disabled in configuration.',
            'risk_score': risk_score,
            'severity': severity,
            'explanation_summary': summary,
            'top_contributors': top_contributors
        }

    if risk_score >= threshold_high:
        reasons_text = ", ".join(top_contributors) if top_contributors else "Anomalous behavioural/contextual signals"
        return {
            'action': ACTION_STEP_UP_OTP,
            'requires_otp': True,
            'reason': f"Elevated login risk ({int(round(risk_score * 100))}%). Triggered by: {reasons_text}.",
            'risk_score': risk_score,
            'severity': severity,
            'explanation_summary': summary,
            'top_contributors': top_contributors
        }
    else:
        return {
            'action': ACTION_ALLOW,
            'requires_otp': False,
            'reason': f"Low risk login ({int(round(risk_score * 100))}%). Behaviour matches established baseline.",
            'risk_score': risk_score,
            'severity': severity,
            'explanation_summary': summary,
            'top_contributors': top_contributors
        }
