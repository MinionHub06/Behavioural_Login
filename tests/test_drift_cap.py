import pytest
from app.services.baseline_service import apply_rate_capped_drift

def test_drift_cap_restricts_large_shift():
    prev_baseline = {
        'avg_dwell_time': 100.0,
        'avg_flight_time': 120.0,
        'typing_speed': 50.0,
        'avg_velocity': 400.0
    }

    # Attacker tries to shift dwell time from 100 to 300 (+200% jump)
    candidate_baseline = {
        'avg_dwell_time': 300.0,
        'avg_flight_time': 300.0,
        'typing_speed': 10.0,
        'avg_velocity': 1200.0
    }

    # Max drift cap 10% (0.10)
    capped = apply_rate_capped_drift(prev_baseline, candidate_baseline, max_drift_rate=0.10)

    # 100 + 10% = 110.0 max
    assert capped['avg_dwell_time'] == 110.0
    # 120 + 10% = 132.0 max
    assert capped['avg_flight_time'] == 132.0
    # 50 - 10% = 45.0 min
    assert capped['typing_speed'] == 45.0
    # 400 + 10% = 440.0 max
    assert capped['avg_velocity'] == 440.0

def test_drift_cap_preserves_small_natural_changes():
    prev_baseline = {
        'avg_dwell_time': 100.0,
        'avg_flight_time': 120.0,
        'typing_speed': 50.0
    }

    # Small normal user variation (+3% dwell, -2% flight)
    candidate_baseline = {
        'avg_dwell_time': 103.0,
        'avg_flight_time': 117.6,
        'typing_speed': 51.0
    }

    capped = apply_rate_capped_drift(prev_baseline, candidate_baseline, max_drift_rate=0.10)

    assert capped['avg_dwell_time'] == 103.0
    assert capped['avg_flight_time'] == 117.6
    assert capped['typing_speed'] == 51.0

def test_multi_step_slow_mimicry_drift_suppression():
    baseline = {'avg_dwell_time': 100.0}
    max_drift = 0.10  # 10%

    # Attacker injects target = 250.0 for 5 consecutive rounds
    for _ in range(5):
        candidate = {'avg_dwell_time': 250.0}
        baseline = apply_rate_capped_drift(baseline, candidate, max_drift_rate=max_drift)

    # In 5 rounds, capped drift shifts from 100 -> 110 -> 121 -> 133.1 -> 146.41 -> 161.05
    # Whereas uncapped would have immediately jumped to 250.0
    assert baseline['avg_dwell_time'] < 165.0
    assert baseline['avg_dwell_time'] > 155.0
