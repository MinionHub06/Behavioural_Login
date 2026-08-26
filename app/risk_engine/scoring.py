import math
from typing import Dict, Any, Optional, List

DEFAULT_RISK_WEIGHTS = {
    'keystroke': 0.25,
    'mouse': 0.25,
    'device': 0.20,
    'location': 0.15,
    'time': 0.15
}

KEYSTROKE_FEATURES_FOR_RISK = [
    'avg_dwell_time', 'std_dwell_time',
    'avg_flight_time', 'std_flight_time',
    'typing_speed', 'typing_speed_variance'
]

MOUSE_FEATURES_FOR_RISK = [
    'avg_velocity', 'std_velocity',
    'avg_acceleration',
    'avg_curvature', 'jitter_score',
    'avg_pause_duration', 'total_path_length'
]

def normalized_feature_anomaly(
    current_val: Optional[float],
    baseline_mean: Optional[float],
    baseline_std: Optional[float] = None,
    z_threshold: float = 3.0,
    min_std: float = 1e-4
) -> Optional[float]:
    """
    Computes a bounded (0.0 to 1.0) normalized anomaly score for a single numerical feature.
    Safely rejects None, NaN, and Infinity.
    """
    if current_val is None or baseline_mean is None:
        return None
    if not isinstance(current_val, (int, float)) or not isinstance(baseline_mean, (int, float)):
        return None
    if math.isnan(current_val) or math.isinf(current_val) or math.isnan(baseline_mean) or math.isinf(baseline_mean):
        return None

    diff = abs(float(current_val) - float(baseline_mean))

    if baseline_std is not None and isinstance(baseline_std, (int, float)) and not math.isnan(baseline_std) and not math.isinf(baseline_std):
        scale = max(abs(float(baseline_std)), min_std)
    else:
        scale = max(abs(float(baseline_mean)) * 0.25, 1.0)

    z_score = diff / scale
    anomaly = min(z_score / max(z_threshold, 1.0), 1.0)
    return round(anomaly, 4)

def calculate_keystroke_anomaly(
    current_keystroke: Optional[Dict[str, Any]],
    keystroke_baseline: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Computes aggregate keystroke rhythm anomaly score (0.0 to 1.0)."""
    if not current_keystroke or not keystroke_baseline:
        return {'score': 0.0, 'features_compared': 0, 'available': False}

    scores = []
    for feature in KEYSTROKE_FEATURES_FOR_RISK:
        cur_val = current_keystroke.get(feature)
        base_mean = keystroke_baseline.get(feature)
        base_std = keystroke_baseline.get('std_' + feature.replace('avg_', '')) if 'avg_' in feature else None

        score = normalized_feature_anomaly(cur_val, base_mean, base_std)
        if score is not None:
            scores.append(score)

    if not scores:
        return {'score': 0.0, 'features_compared': 0, 'available': False}

    avg_score = round(sum(scores) / len(scores), 4)
    return {'score': avg_score, 'features_compared': len(scores), 'available': True}

def calculate_mouse_anomaly(
    current_mouse: Optional[Dict[str, Any]],
    mouse_baseline: Optional[Dict[str, Any]]
) -> Dict[str, Any]:
    """Computes aggregate mouse movement kinetics anomaly score (0.0 to 1.0)."""
    if not current_mouse or not mouse_baseline or current_mouse.get('sample_available') is False:
        return {'score': 0.0, 'features_compared': 0, 'available': False}

    scores = []
    for feature in MOUSE_FEATURES_FOR_RISK:
        cur_val = current_mouse.get(feature)
        base_mean = mouse_baseline.get(feature)
        base_std = mouse_baseline.get('std_' + feature.replace('avg_', '')) if 'avg_' in feature else None

        score = normalized_feature_anomaly(cur_val, base_mean, base_std)
        if score is not None:
            scores.append(score)

    if not scores:
        return {'score': 0.0, 'features_compared': 0, 'available': False}

    avg_score = round(sum(scores) / len(scores), 4)
    return {'score': avg_score, 'features_compared': len(scores), 'available': True}

def calculate_device_anomaly(context_eval: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluates device anomaly score (0.0 for known/unknown, 1.0 for new)."""
    if not context_eval:
        return {'score': 0.0, 'available': False}

    status = context_eval.get('device_status', 'unknown')
    if status == 'known':
        return {'score': 0.0, 'available': True}
    elif status == 'new':
        return {'score': 1.0, 'available': True}
    else:  # 'unknown'
        return {'score': 0.0, 'available': True}

def calculate_location_anomaly(context_eval: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluates geographic location anomaly score (0.0 for known/unknown, 1.0 for new)."""
    if not context_eval:
        return {'score': 0.0, 'available': False}

    status = context_eval.get('location_status', 'unknown')
    if status == 'known':
        return {'score': 0.0, 'available': True}
    elif status == 'new':
        return {'score': 1.0, 'available': True}
    else:  # 'unknown'
        return {'score': 0.0, 'available': True}

def calculate_time_anomaly(context_eval: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Evaluates login time anomaly score (0.0 for usual/unknown, 1.0 for unusual)."""
    if not context_eval:
        return {'score': 0.0, 'available': False}

    status = context_eval.get('time_status', 'unknown')
    if status == 'usual':
        return {'score': 0.0, 'available': True}
    elif status == 'unusual':
        return {'score': 1.0, 'available': True}
    else:  # 'unknown'
        return {'score': 0.0, 'available': True}

def validate_weights(weights: Dict[str, float]) -> bool:
    """Validates that weights dictionary is positive and sums to approximately 1.0."""
    if not weights or not isinstance(weights, dict):
        return False
    total = sum(weights.values())
    return abs(total - 1.0) < 0.01

def calculate_combined_risk(
    signals: Dict[str, Dict[str, Any]],
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Computes overall risk score (0.0 to 1.0) using available signals and proportional weight redistribution.
    """
    if weights is None:
        weights = DEFAULT_RISK_WEIGHTS

    available_signals = {k: sig for k, sig in signals.items() if sig.get('available') is True}

    if not available_signals:
        return {
            'risk_score': None,
            'status': 'insufficient_data',
            'signals': signals
        }

    available_weight_sum = sum(weights.get(k, 0.0) for k in available_signals)

    if available_weight_sum <= 0:
        return {
            'risk_score': None,
            'status': 'insufficient_data',
            'signals': signals
        }

    weighted_risk = 0.0
    for key, sig in available_signals.items():
        original_w = weights.get(key, 0.0)
        norm_w = original_w / available_weight_sum
        weighted_risk += norm_w * float(sig.get('score', 0.0))

    clamped_risk = max(0.0, min(round(weighted_risk, 4), 1.0))

    return {
        'risk_score': clamped_risk,
        'status': 'evaluated',
        'signals': signals
    }

def evaluate_login_risk(
    user_id: int,
    current_keystroke: Optional[Dict[str, Any]] = None,
    current_mouse: Optional[Dict[str, Any]] = None,
    context_eval: Optional[Dict[str, Any]] = None,
    weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Evaluates current login attempt against authenticated user's established baseline.
    Computes individual signal anomalies and combined risk score.
    """
    from app.services.baseline_service import get_user_baseline

    user_baseline = get_user_baseline(user_id)

    from app.risk_engine.explanation import generate_explanation

    # Handle insufficient baseline explicitly
    if user_baseline.get('status') == 'insufficient_data':
        signals = {
            'keystroke': {'score': 0.0, 'available': False},
            'mouse': {'score': 0.0, 'available': False},
            'device': calculate_device_anomaly(context_eval),
            'location': calculate_location_anomaly(context_eval),
            'time': calculate_time_anomaly(context_eval)
        }
        res = {
            'user_id': user_id,
            'risk_score': None,
            'status': 'insufficient_baseline',
            'signals': signals
        }
        res['explanation'] = generate_explanation(res, weights)
        return res

    ks_baseline = user_baseline.get('keystroke', {})
    ms_baseline = user_baseline.get('mouse', {})

    signals = {
        'keystroke': calculate_keystroke_anomaly(current_keystroke, ks_baseline),
        'mouse': calculate_mouse_anomaly(current_mouse, ms_baseline),
        'device': calculate_device_anomaly(context_eval),
        'location': calculate_location_anomaly(context_eval),
        'time': calculate_time_anomaly(context_eval)
    }

    result = calculate_combined_risk(signals, weights)
    result['user_id'] = user_id
    result['explanation'] = generate_explanation(result, weights)
    return result
