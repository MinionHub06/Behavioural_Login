from typing import Dict, Any, List, Optional
from app.risk_engine.scoring import DEFAULT_RISK_WEIGHTS

SIGNAL_DISPLAY_LABELS = {
    'keystroke': 'Keystroke behaviour',
    'mouse': 'Mouse behaviour',
    'device': 'Device',
    'location': 'Location',
    'time': 'Login time'
}

SEVERITY_LEVELS = [
    (0.00, 0.19, 'normal'),
    (0.20, 0.49, 'slightly unusual'),
    (0.50, 0.74, 'moderately unusual'),
    (0.75, 1.00, 'highly unusual')
]

def classify_severity(score: Optional[float]) -> str:
    """Classifies a 0.0 to 1.0 score into a deterministic severity label."""
    if score is None:
        return 'unknown'
    clamped = max(0.0, min(float(score), 1.0))
    for low, high, label in SEVERITY_LEVELS:
        if low <= clamped <= high:
            return label
    return 'highly unusual'

def get_signal_status_text(
    signal_key: str,
    score: Optional[float],
    available: bool,
    raw_status: Optional[str] = None
) -> str:
    """Generates context-aware human-readable status text for a specific signal."""
    if not available or score is None:
        return f"{SIGNAL_DISPLAY_LABELS.get(signal_key, signal_key)} information unavailable"

    severity = classify_severity(score)

    if signal_key == 'device':
        if score >= 0.8:
            return "New device"
        elif score == 0.0:
            return "Known device"
        return "Unrecognized device signature"

    elif signal_key == 'location':
        if score >= 0.8:
            return "New location"
        elif score == 0.0:
            return "Known location"
        return "Unrecognized location signature"

    elif signal_key == 'time':
        if score >= 0.8:
            return "Login time is outside the user's usual pattern"
        elif score == 0.0:
            return "Login time is within the user's usual pattern"
        return "Login time differs slightly from usual pattern"

    elif signal_key == 'keystroke':
        if severity == 'normal':
            return "Typing rhythm is close to the user's baseline"
        elif severity == 'slightly unusual':
            return "Typing rhythm differs slightly from the user's baseline"
        elif severity == 'moderately unusual':
            return "Typing rhythm differs moderately from the user's baseline"
        else:
            return "Typing rhythm differs substantially from the user's baseline"

    elif signal_key == 'mouse':
        if severity == 'normal':
            return "Mouse movement is close to the user's baseline"
        elif severity == 'slightly unusual':
            return "Mouse movement differs slightly from the user's baseline"
        elif severity == 'moderately unusual':
            return "Mouse movement differs moderately from the user's baseline"
        else:
            return "Mouse movement differs substantially from the user's baseline"

    return f"{SIGNAL_DISPLAY_LABELS.get(signal_key, signal_key)} score: {score}"

def generate_explanation(
    risk_result: Dict[str, Any],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Generates a deterministic, explainable-by-design feature attribution object
    and human-readable summary from the Step 7 risk score evaluation.
    """
    if weights is None:
        weights = DEFAULT_RISK_WEIGHTS

    status = risk_result.get('status')
    if status == 'insufficient_baseline':
        return {
            'overall_severity': 'insufficient baseline',
            'summary': 'Insufficient historical logins to establish a behavioural baseline.',
            'top_contributors': [],
            'signals': []
        }

    risk_score = risk_result.get('risk_score', 0.0)
    signals = risk_result.get('signals', {})

    available_signals = {k: v for k, v in signals.items() if v.get('available') is True}
    available_weight_sum = sum(weights.get(k, 0.0) for k in available_signals)

    signal_explanations = []
    total_contribution = 0.0

    # Calculate raw contributions
    for key, label in SIGNAL_DISPLAY_LABELS.items():
        sig_data = signals.get(key, {})
        avail = sig_data.get('available', False)
        score = sig_data.get('score')

        if avail and available_weight_sum > 0:
            eff_weight = round(weights.get(key, 0.0) / available_weight_sum, 4)
            contrib = round((score if score is not None else 0.0) * eff_weight, 4)
        else:
            eff_weight = 0.0
            contrib = 0.0

        total_contribution += contrib
        status_text = get_signal_status_text(key, score, avail)
        severity = classify_severity(score) if avail else 'unavailable'

        signal_explanations.append({
            'signal': key,
            'label': label,
            'score': score if avail else None,
            'available': avail,
            'effective_weight': eff_weight,
            'contribution': contrib,
            'relative_contribution': 0.0,  # Computed in second pass
            'severity': severity,
            'status': status_text
        })

    # Calculate relative contributions (percentage of total risk contribution)
    for sig in signal_explanations:
        if sig['available'] and total_contribution > 0:
            sig['relative_contribution'] = round(sig['contribution'] / total_contribution, 4)
        else:
            sig['relative_contribution'] = 0.0

    # Sort available signals by contribution descending
    active_signals = [s for s in signal_explanations if s['available']]
    sorted_signals = sorted(active_signals, key=lambda s: (s['contribution'], s['score'] or 0.0), reverse=True)

    # Filter top contributors (max 3, only if score > 0 or contribution > 0)
    top_contributors = []
    for s in sorted_signals:
        if len(top_contributors) >= 3:
            break
        if s['contribution'] > 0 or (s['score'] is not None and s['score'] > 0):
            top_contributors.append(s['label'])

    overall_severity = classify_severity(risk_score)

    # Generate human-readable summary sentence
    if risk_score is None or overall_severity == 'normal' or not top_contributors:
        summary = "Login behaviour is consistent with the user's established pattern."
    elif overall_severity == 'slightly unusual':
        contrib_str = ", ".join(top_contributors[:2]).lower()
        summary = f"Login behaviour shows slight variation in {contrib_str}."
    elif overall_severity == 'moderately unusual':
        contrib_str = ", ".join(top_contributors).lower()
        summary = f"Login behaviour differs moderately due to {contrib_str}."
    else:
        contrib_str = ", ".join(top_contributors).lower()
        summary = f"Login behaviour differs substantially due to {contrib_str}."

    return {
        'risk_score': risk_score,
        'overall_severity': overall_severity,
        'summary': summary,
        'top_contributors': top_contributors,
        'signals': signal_explanations
    }
