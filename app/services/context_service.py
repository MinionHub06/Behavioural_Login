import hashlib
import ipaddress
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
from flask import Request

def get_client_ip(request: Request) -> str:
    """
    Extracts client IP address safely.
    In local development, uses remote_addr to avoid header spoofing.
    """
    ip = request.remote_addr
    if not ip or ip == '::1':
        return '127.0.0.1'
    return ip

def is_private_ip(ip_str: str) -> bool:
    """Returns True if the IP is loopback, private, or local."""
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return ip_obj.is_private or ip_obj.is_loopback
    except ValueError:
        return True

def get_location_from_ip(ip_str: str) -> str:
    """
    Location abstraction layer.
    For local/private IPs, returns 'LOCAL'.
    If no external geolocation provider is configured, returns 'UNKNOWN'.
    Does not invent geographic coordinates.
    """
    if is_private_ip(ip_str):
        return 'LOCAL'
    # Reserved placeholder for future production GeoIP lookup (e.g. MaxMind / GeoLite2)
    return 'UNKNOWN'

def generate_device_id(request: Request, client_hints: Optional[Dict[str, Any]] = None) -> str:
    """
    Generates a deterministic, lightweight prototype device signature hash (SHA-256).
    Combines normalized User-Agent, Accept-Language, platform, and optional client hints.
    """
    ua = request.headers.get('User-Agent', '').strip().lower()
    lang = request.headers.get('Accept-Language', '').split(',')[0].strip().lower()

    platform = ''
    screen_res = ''
    tz_offset = ''

    if client_hints and isinstance(client_hints, dict):
        platform = str(client_hints.get('platform', '')).strip().lower()
        screen_res = str(client_hints.get('screen_res', '')).strip().lower()
        tz_offset = str(client_hints.get('tz_offset', '')).strip().lower()

    raw_signature = f"{ua}|{lang}|{platform}|{screen_res}|{tz_offset}"
    return hashlib.sha256(raw_signature.encode('utf-8')).hexdigest()

def is_hour_in_usual_range(current_hour: int, historical_hours: List[int]) -> bool:
    """
    Determines if current_hour falls within the user's historical login pattern.
    Handles 24-hour circular wraparound across midnight (e.g., 23, 0, 1).
    Allows a 2-hour tolerance window around known historical hours.
    """
    if not historical_hours:
        return True

    for h in historical_hours:
        # Distance on a 24-hour clock
        diff = abs(current_hour - h)
        circular_diff = min(diff, 24 - diff)
        if circular_diff <= 2:
            return True
    return False

def evaluate_context_signals(
    user_id: int,
    current_device_id: str,
    current_ip: str,
    current_location: str,
    current_login_time: datetime,
    historical_samples: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Evaluates current login contextual environment against user's historical context records.
    Computes flags for new_device, new_location, and unusual_time.
    """
    current_hour = current_login_time.hour
    login_time_str = current_login_time.strftime('%Y-%m-%d %H:%M:%S')

    # First Login / No History
    if not historical_samples:
        return {
            'user_id': user_id,
            'device_id': current_device_id,
            'device_status': 'unknown',
            'ip_address': current_ip,
            'location': current_location,
            'location_status': 'unknown',
            'login_time': login_time_str,
            'login_hour': current_hour,
            'time_status': 'unknown',
            'new_device': False,
            'new_location': False,
            'unusual_time': False
        }

    # 1. Device Evaluation
    known_devices = {s['device_id'] for s in historical_samples if 'device_id' in s}
    if current_device_id in known_devices:
        device_status = 'known'
        new_device = False
    else:
        device_status = 'new'
        new_device = True

    # 2. Location Evaluation
    if current_location in ('LOCAL', 'UNKNOWN'):
        location_status = 'unknown'
        new_location = False
    else:
        known_locations = {s['location'] for s in historical_samples if s.get('location') not in ('LOCAL', 'UNKNOWN')}
        if not known_locations:
            location_status = 'unknown'
            new_location = False
        elif current_location in known_locations:
            location_status = 'known'
            new_location = False
        else:
            location_status = 'new'
            new_location = True

    # 3. Time Evaluation (Requires minimum 3 prior logins for statistical baseline confidence)
    MIN_HISTORICAL_SAMPLES_FOR_TIME = 3
    if len(historical_samples) < MIN_HISTORICAL_SAMPLES_FOR_TIME:
        time_status = 'unknown'
        unusual_time = False
    else:
        historical_hours = [s['login_hour'] for s in historical_samples if 'login_hour' in s]
        if is_hour_in_usual_range(current_hour, historical_hours):
            time_status = 'usual'
            unusual_time = False
        else:
            time_status = 'unusual'
            unusual_time = True

    return {
        'user_id': user_id,
        'device_id': current_device_id,
        'device_status': device_status,
        'ip_address': current_ip,
        'location': current_location,
        'location_status': location_status,
        'login_time': login_time_str,
        'login_hour': current_hour,
        'time_status': time_status,
        'new_device': new_device,
        'new_location': new_location,
        'unusual_time': unusual_time
    }
