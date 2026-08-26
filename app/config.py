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

    # Risk Scoring Engine Configuration
    RISK_WEIGHT_KEYSTROKE = float(os.environ.get('RISK_WEIGHT_KEYSTROKE', 0.25))
    RISK_WEIGHT_MOUSE = float(os.environ.get('RISK_WEIGHT_MOUSE', 0.25))
    RISK_WEIGHT_DEVICE = float(os.environ.get('RISK_WEIGHT_DEVICE', 0.20))
    RISK_WEIGHT_LOCATION = float(os.environ.get('RISK_WEIGHT_LOCATION', 0.15))
    RISK_WEIGHT_TIME = float(os.environ.get('RISK_WEIGHT_TIME', 0.15))
    
    Z_THRESHOLD = float(os.environ.get('Z_THRESHOLD', 3.0))
    MIN_STD = float(os.environ.get('MIN_STD', 1e-4))
