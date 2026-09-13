import time
import secrets
from typing import Tuple, Optional, Dict, Any
from app.config import Config
from app.models.otp import (
    save_otp,
    get_latest_otp,
    increment_otp_attempts,
    mark_otp_used,
    delete_user_otps
)

def generate_otp_for_user(user_id: int, expiry_seconds: Optional[int] = None) -> str:
    """
    Generates a cryptographically secure 6-digit numeric OTP code,
    persists it with expiration timestamp, and returns the code.
    """
    if expiry_seconds is None:
        expiry_seconds = Config.OTP_EXPIRY_SECONDS

    # Cryptographically secure 6-digit number
    otp_code = str(secrets.randbelow(900000) + 100000)
    expires_at = time.time() + expiry_seconds

    save_otp(user_id, otp_code, expires_at)
    return otp_code

def verify_user_otp(
    user_id: int,
    submitted_code: str,
    max_attempts: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Verifies a user-submitted OTP code.
    Enforces expiration and maximum failure attempt limits.
    Returns (is_valid, message).
    """
    if max_attempts is None:
        max_attempts = Config.OTP_MAX_ATTEMPTS

    if not submitted_code or not str(submitted_code).strip():
        return False, "Please enter the verification code."

    record = get_latest_otp(user_id)
    if not record:
        return False, "No active verification session. Please log in again."

    # Check expiration
    if time.time() > float(record['expires_at']):
        return False, "Verification code has expired. Please request a new code."

    # Check maximum attempt lockout
    if record['attempts'] >= max_attempts:
        return False, "Too many failed attempts. Please request a new verification code."

    # Check match
    clean_code = str(submitted_code).strip()
    if clean_code == record['otp_code']:
        mark_otp_used(record['id'])
        return True, "Identity verified successfully."
    else:
        new_attempts = increment_otp_attempts(record['id'])
        remaining = max(0, max_attempts - new_attempts)
        if remaining > 0:
            return False, f"Invalid verification code. {remaining} attempt(s) remaining."
        else:
            return False, "Maximum attempts reached. Please request a new code."

def get_active_otp(user_id: int) -> Optional[Dict[str, Any]]:
    """Retrieves unexpired active OTP record for developer demo display."""
    record = get_latest_otp(user_id)
    if record and time.time() <= float(record['expires_at']):
        return record
    return None
