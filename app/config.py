import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file if present
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """Base application configuration class."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    
    # SQLite Database Configuration
    DATABASE_PATH = os.environ.get(
        'DATABASE_PATH', 
        str(BASE_DIR / 'database' / 'cybersec.db')
    )

    # Behavioural Baseline Configuration
    BASELINE_DECAY_FACTOR = float(os.environ.get('BASELINE_DECAY_FACTOR', 0.8))
    BASELINE_MAX_DRIFT_RATE = float(os.environ.get('BASELINE_MAX_DRIFT_RATE', 0.10))  # 10% max drift per update

    # Risk Scoring Engine Configuration
    RISK_WEIGHT_KEYSTROKE = float(os.environ.get('RISK_WEIGHT_KEYSTROKE', 0.25))
    RISK_WEIGHT_MOUSE = float(os.environ.get('RISK_WEIGHT_MOUSE', 0.25))
    RISK_WEIGHT_DEVICE = float(os.environ.get('RISK_WEIGHT_DEVICE', 0.20))
    RISK_WEIGHT_LOCATION = float(os.environ.get('RISK_WEIGHT_LOCATION', 0.15))
    RISK_WEIGHT_TIME = float(os.environ.get('RISK_WEIGHT_TIME', 0.15))
    
    Z_THRESHOLD = float(os.environ.get('Z_THRESHOLD', 3.0))
    MIN_STD = float(os.environ.get('MIN_STD', 1e-4))

    # Decision Engine & Step-Up Verification Thresholds
    RISK_THRESHOLD_LOW = float(os.environ.get('RISK_THRESHOLD_LOW', 0.35))
    RISK_THRESHOLD_HIGH = float(os.environ.get('RISK_THRESHOLD_HIGH', 0.50))
    RISK_STEPUP_ENABLED = os.environ.get('RISK_STEPUP_ENABLED', 'true').lower() in ('true', '1', 'yes')

    # OTP Verification Settings
    OTP_EXPIRY_SECONDS = int(os.environ.get('OTP_EXPIRY_SECONDS', 300))  # 5 minutes
    OTP_MAX_ATTEMPTS = int(os.environ.get('OTP_MAX_ATTEMPTS', 3))

