import math
from typing import List, Dict, Any, Optional
from app.models.keystroke import get_user_keystroke_features
from app.models.mouse import get_user_mouse_features
from app.models.context import get_user_context_features
from app.models.baseline import save_or_update_baseline, get_user_baseline_record

KEYSTROKE_NUMERIC_FEATURES = [
    'avg_dwell_time', 'std_dwell_time', 'min_dwell_time', 'max_dwell_time',
    'avg_flight_time', 'std_flight_time', 'min_flight_time', 'max_flight_time',
    'total_typing_duration', 'typing_speed', 'typing_speed_variance', 'sample_count'
]

MOUSE_NUMERIC_FEATURES = [
    'avg_velocity', 'std_velocity', 'min_velocity', 'max_velocity',
    'avg_acceleration', 'std_acceleration',
    'avg_curvature', 'std_curvature', 'total_direction_change',
    'jitter_score',
    'pause_count', 'avg_pause_duration', 'max_pause_duration', 'total_pause_duration',
    'total_path_length', 'tracking_duration', 'point_count'
]

def weighted_mean(values: List[float], weights: List[float]) -> float:
    """
    Calculates the weighted arithmetic mean of a sequence of values and corresponding weights.
    Ignores None, non-numeric, NaN, and Infinity entries safely.
    """
    if not values or not weights or len(values) != len(weights):
        return 0.0

    valid_sum = 0.0
    weight_sum = 0.0

    for val, w in zip(values, weights):
        if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
            continue
        if math.isnan(val) or math.isinf(val):
            continue
        valid_sum += w * float(val)
        weight_sum += w

    if weight_sum <= 0:
        return 0.0

    return Number_Format(valid_sum / weight_sum)

def Number_Format(val: float, decimals: int = 2) -> float:
    """Helper to round floats cleanly."""
    return round(float(val), decimals)

def calculate_keystroke_baseline(
    keystroke_samples: List[Dict[str, Any]],
    decay_factor: float = 0.8
) -> Dict[str, Any]:
    """
    Computes recency-weighted baseline features for keystroke dynamics.
    Samples are expected to be ordered newest to oldest.
    """
    if not keystroke_samples:
        return {}

    weights = [math.pow(decay_factor, idx) for idx in range(len(keystroke_samples))]
    baseline = {}

    for feature in KEYSTROKE_NUMERIC_FEATURES:
        vals = [s.get(feature) for s in keystroke_samples if feature in s]
        feature_weights = weights[:len(vals)]
        if vals:
            baseline[feature] = weighted_mean(vals, feature_weights)

    return baseline

def calculate_mouse_baseline(
    mouse_samples: List[Dict[str, Any]],
    decay_factor: float = 0.8
) -> Dict[str, Any]:
    """
    Computes recency-weighted baseline features for mouse kinetics.
    Samples are expected to be ordered newest to oldest.
    """
    if not mouse_samples:
        return {}

    weights = [math.pow(decay_factor, idx) for idx in range(len(mouse_samples))]
    baseline = {}

    for feature in MOUSE_NUMERIC_FEATURES:
        vals = [s.get(feature) for s in mouse_samples if feature in s]
        feature_weights = weights[:len(vals)]
        if vals:
            dec = 4 if 'curvature' in feature or 'jitter' in feature else 2
            mean_val = weighted_mean(vals, feature_weights)
            baseline[feature] = round(mean_val, dec)

    return baseline

def calculate_context_baseline(context_samples: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes contextual baseline knowledge (known devices, known locations, login hour distribution).
    Does NOT average string identifiers or IP addresses.
    """
    if not context_samples:
        return {
            'known_devices': [],
            'known_locations': [],
            'login_hour_distribution': {}
        }

    known_devices = set()
    known_locations = set()
    hour_distribution = {}

    for sample in context_samples:
        dev_id = sample.get('device_id')
        if dev_id and dev_id not in ('unknown', ''):
            known_devices.add(dev_id)

        loc = sample.get('location')
        if loc and loc not in ('LOCAL', 'UNKNOWN', ''):
            known_locations.add(loc)

        if 'login_hour' in sample and sample['login_hour'] is not None:
            hour_key = str(int(sample['login_hour']))
            hour_distribution[hour_key] = hour_distribution.get(hour_key, 0) + 1

    return {
        'known_devices': sorted(list(known_devices)),
        'known_locations': sorted(list(known_locations)),
        'login_hour_distribution': hour_distribution
    }

def apply_rate_capped_drift(
    previous_baseline: Dict[str, Any],
    candidate_baseline: Dict[str, Any],
    max_drift_rate: float = 0.10,
    min_floor: float = 0.005
) -> Dict[str, Any]:
    """
    Caps the maximum shift of any numeric baseline feature per update cycle to max_drift_rate (e.g. 10%).
    This rate-capping protects against adversarial slow mimicry baseline poisoning while allowing
    legitimate gradual user behavioral adaptation.
    """
    if not previous_baseline or not isinstance(previous_baseline, dict):
        return candidate_baseline

    capped = {}
    for k, cand_val in candidate_baseline.items():
        if cand_val is None or not isinstance(cand_val, (int, float)):
            capped[k] = cand_val
            continue

        prev_val = previous_baseline.get(k)
        if prev_val is None or not isinstance(prev_val, (int, float)):
            capped[k] = cand_val
            continue

        prev_float = float(prev_val)
        cand_float = float(cand_val)
        max_delta = max(abs(prev_float) * max_drift_rate, min_floor)

        lower_bound = prev_float - max_delta
        upper_bound = prev_float + max_delta

        clamped_val = max(lower_bound, min(cand_float, upper_bound))
        dec = 4 if 'curvature' in k or 'jitter' in k else 2
        capped[k] = round(clamped_val, dec)

    return capped

def create_or_update_user_baseline(
    user_id: int,
    decay_factor: float = 0.8,
    drift_capped: bool = True,
    max_drift_rate: float = 0.10
) -> Dict[str, Any]:
    """
    Retrieves historical samples for user, calculates rolling recency-weighted baseline,
    applies rate-capped drift bounding if enabled, persists/updates database record,
    and returns the baseline structure.
    """
    existing_record = get_user_baseline_record(user_id)

    keystroke_samples = get_user_keystroke_features(user_id)
    mouse_samples = get_user_mouse_features(user_id)
    context_samples = get_user_context_features(user_id)

    keystroke_cand = calculate_keystroke_baseline(keystroke_samples, decay_factor)
    mouse_cand = calculate_mouse_baseline(mouse_samples, decay_factor)
    context_bl = calculate_context_baseline(context_samples)

    # Apply rate-capped drift if prior baseline exists
    if drift_capped and existing_record and existing_record.get('status') in ('initial', 'established'):
        keystroke_bl = apply_rate_capped_drift(existing_record.get('keystroke', {}), keystroke_cand, max_drift_rate)
        mouse_bl = apply_rate_capped_drift(existing_record.get('mouse', {}), mouse_cand, max_drift_rate)
    else:
        keystroke_bl = keystroke_cand
        mouse_bl = mouse_cand

    total_samples = max(len(keystroke_samples), len(mouse_samples), len(context_samples))

    if total_samples == 0:
        status = "insufficient_data"
    elif total_samples == 1:
        status = "initial"
    else:
        status = "established"

    baseline_payload = {
        'status': status,
        'sample_count': total_samples,
        'keystroke': keystroke_bl,
        'mouse': mouse_bl,
        'context': context_bl
    }

    save_or_update_baseline(user_id, baseline_payload)
    return get_user_baseline(user_id)


def get_user_baseline(user_id: int) -> Dict[str, Any]:
    """
    Retrieves current baseline structure for user.
    If no record exists, returns a default 'insufficient_data' dictionary.
    """
    record = get_user_baseline_record(user_id)
    if not record:
        return {
            'user_id': user_id,
            'baseline_version': 0,
            'sample_count': 0,
            'status': 'insufficient_data',
            'keystroke': {},
            'mouse': {},
            'context': {
                'known_devices': [],
                'known_locations': [],
                'login_hour_distribution': {}
            },
            'created_at': None,
            'updated_at': None
        }

    return record
