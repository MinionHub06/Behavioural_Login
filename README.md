# Behavioural Login Verification System

## Short Description
A Cyber Security academic project implementing continuous user authentication using **Keystroke Dynamics**, **Mouse Movement kinetics**, and **Contextual Risk Signals** to calculate adaptive risk scores and trigger step-up verification.

## Implementation Status
- **Step 1: Flask Project Foundation** - COMPLETE
- **Step 2: Basic Conventional Authentication** - COMPLETE
- **Step 3: Keystroke Dynamics Capture & Feature Extraction** - COMPLETE
- **Step 4: Mouse Movement Dynamics Capture & Feature Extraction** - COMPLETE
- **Step 5: Contextual Login Signals (Device, Location, Time)** - COMPLETE
- **Step 6: Per-User Rolling Behavioural Baseline** - COMPLETE
- **Step 7: Risk Scoring Engine** - COMPLETE
- **Step 8: Explainable Risk Score / Explanation Module** - COMPLETE
- *Future Steps: Risk-based decision engine, OTP step-up verification, rate-capped baseline adaptation, attack simulation, evaluation* - NOT IMPLEMENTED YET

---

## Step 3 - Keystroke Dynamics
Captures non-sensitive aggregate typing rhythm timing features (dwell time, flight time, typing speed, and speed variance). Passwords and individual key identities are **NEVER** recorded or stored.

---

## Step 4 - Mouse Movement Dynamics
Captures fine-motor kinetics (velocity, acceleration, path curvature, jitter score, and pause patterns). Raw coordinates `(x, y)` are kept temporarily in browser memory and are **NEVER** stored in SQLite or transmitted.

---

## Step 5 - Contextual Risk Signals
Evaluates physical and environmental context: `device_id` (SHA-256 hash of browser signature), client IP / location abstraction (`LOCAL`/`UNKNOWN`), and UTC login hour vs 24-hour circular distribution. Neutral `unknown` flags on first login prevent false positive alarms.

---

## Step 6 - Per-User Rolling Behavioural Baseline
Establishes a statistical profile of normal user behavior using **exponential decay recency weighting** ($\text{decay\_factor} = 0.8$) and weighted arithmetic means across typing dynamics, mouse kinetics, and contextual distributions.

---

## Step 7 - Risk Scoring Engine
Calculates standardized deviations ($Z$-scores) bounded between $0.0$ and $1.0$ across keystroke, mouse, device, location, and time signals. Redistributes weights proportionally if any signal is unavailable.

---

## Step 8 - Explainable Risk Score / Explanation Module

### Why Explainability is Required
Every calculated risk score must come with a clear, human-readable explanation identifying which signals contributed to the risk level. This eliminates "black box" decisions and provides auditability during cybersecurity reviews.

### Signal Contribution Calculation
Each available signal's raw contribution reflects both its anomaly score and its effective weight (after any missing-signal weight redistribution):
$$\text{contribution}_i = \text{score}_i \times \text{effective\_weight}_i$$

Relative contribution (percentage of total observed risk):
$$\text{relative\_contribution}_i = \frac{\text{contribution}_i}{\sum_{k \in \text{available}} \text{contribution}_k} \quad (\text{returns } 0.0 \text{ if total contribution } = 0)$$

### Severity Levels
- **0.00 – 0.19**: `normal`
- **0.20 – 0.49**: `slightly unusual`
- **0.50 – 0.74**: `moderately unusual`
- **0.75 – 1.00**: `highly unusual`

### Why SHAP Library is Not Used Yet
The current risk scoring engine is a transparent, explainable-by-design weighted anomaly model. Its feature attributions are computed directly and deterministically from signal scores and weights without needing heavy machine-learning approximations like `shap`.

> **DETERMINISTIC EXPLANATION GUARANTEE**: *The explanation is generated deterministically from the risk engine's signal scores and weights, without random text generation or black-box ML models.*

---

## Database Schema (SQLite: `database/cybersec.db`)

### `risk_scores` Table
```sql
CREATE TABLE IF NOT EXISTS risk_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    keystroke_score REAL,
    mouse_score REAL,
    device_score REAL,
    location_score REAL,
    time_score REAL,
    risk_score REAL,
    status TEXT NOT NULL,
    signals_json TEXT NOT NULL,
    explanation_json TEXT,
    explanation_summary TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
```

---

## Example Risk Score & Explanation Payload
```json
{
    "user_id": 1,
    "risk_score": 0.67,
    "status": "evaluated",
    "explanation": {
        "overall_severity": "moderately unusual",
        "summary": "Login behaviour differs moderately due to device, keystroke behaviour, login time.",
        "top_contributors": ["Device", "Keystroke behaviour", "Login time"],
        "signals": [
            {
                "signal": "device",
                "label": "Device",
                "score": 1.0,
                "available": true,
                "effective_weight": 0.20,
                "contribution": 0.20,
                "relative_contribution": 0.3704,
                "severity": "highly unusual",
                "status": "New device"
            },
            {
                "signal": "keystroke",
                "label": "Keystroke behaviour",
                "score": 0.72,
                "available": true,
                "effective_weight": 0.25,
                "contribution": 0.18,
                "relative_contribution": 0.3333,
                "severity": "moderately unusual",
                "status": "Typing rhythm differs moderately from the user's baseline"
            },
            {
                "signal": "time",
                "label": "Login time",
                "score": 1.0,
                "available": true,
                "effective_weight": 0.15,
                "contribution": 0.15,
                "relative_contribution": 0.2778,
                "severity": "highly unusual",
                "status": "Login time is outside the user's usual pattern"
            }
        ]
    }
}
```

---

## Project Structure
```text
cybersec-project/
│
├── app/
│   ├── __init__.py          # Application Factory (Blueprint & error handler init)
│   ├── config.py            # Risk weights & BASELINE_DECAY_FACTOR config
│   │
│   ├── routes/
│   │   ├── __init__.py      # Blueprint exports
│   │   ├── main.py          # Status & health routes (/, /health)
│   │   ├── auth.py          # Auth routes (/register, /login, /dashboard, /logout)
│   │   └── behavior.py      # API routes (/api/behavior/*, GET /api/baseline, GET /api/risk/latest)
│   │
│   ├── models/
│   │   ├── __init__.py      # DB helper exports
│   │   ├── base.py          # SQLite connection and DB table creation hook
│   │   ├── user.py          # User model & SQL CRUD queries
│   │   ├── keystroke.py     # Keystroke features schema & persistence
│   │   ├── mouse.py         # Mouse features schema & persistence
│   │   ├── context.py       # Context features schema & persistence
│   │   ├── baseline.py      # Behavioural baseline schema & persistence
│   │   └── risk.py          # Risk evaluation & explanation schema/persistence
│   │
│   ├── services/
│   │   ├── __init__.py      # Service exports
│   │   ├── context_service.py  # Context evaluation service
│   │   └── baseline_service.py # Recency-weighted rolling baseline engine
│   │
│   ├── risk_engine/
│   │   ├── __init__.py      # Risk engine exports
│   │   ├── scoring.py       # Distance-from-baseline risk engine
│   │   └── explanation.py   # Explainable risk feature attribution module
│   │
│   ├── templates/
│   │   ├── index.html       # System status page with quick navigation
│   │   ├── register.html    # Registration page
│   │   ├── login.html       # Login page (with active behavioural indicator)
│   │   └── dashboard.html   # Authenticated user dashboard with Risk Explanation UI
│   │
│   └── static/
│       ├── css/
│       │   └── style.css    # Dark theme CSS
│       └── js/
│           ├── main.js      # Frontend health check script
│           ├── keystroke.js # Client-side keystroke timing extraction
│           └── mouse.js     # Client-side mouse dynamics extraction
│
├── database/
│   └── .gitkeep             # Database directory (cybersec.db initialized automatically)
│
├── tests/
│   ├── test_app.py          # Base Flask & health tests (4 tests)
│   ├── test_auth.py         # Authentication test suite (13 tests)
│   ├── test_behavior.py     # Keystroke dynamics unit tests (6 tests)
│   ├── test_mouse.py        # Mouse dynamics unit tests (13 tests)
│   ├── test_context.py      # Contextual risk signal unit tests (7 tests)
│   ├── test_baseline.py     # Rolling baseline unit tests (7 tests)
│   ├── test_risk.py         # Risk scoring engine unit tests (6 tests)
│   └── test_explanation.py  # Explanation module unit tests (5 tests)
│
├── view_db.py               # Clean SQLite database inspector script
├── conftest.py              # Root path configuration for pytest
├── .env.example             # Template for configuration settings
├── .gitignore               # Excludes venv, db, pycache
├── requirements.txt         # Dependencies
├── run.py                   # Development server execution script
└── README.md                # Updated documentation & project status
```

---

## Requirements & Setup
- Python 3.10+
- Flask 3.0+
- python-dotenv
- pytest

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## How to Run Tests
```powershell
pytest
```

## How to Run the Application
```powershell
python run.py
```
*Access application at: `http://127.0.0.1:5000`*

---

## Available Routes
| Route | Method | Access | Description |
|---|---|---|---|
| `/` | GET | Public | Home / system status page |
| `/health` | GET | Public | JSON health check endpoint |
| `/register` | GET, POST | Public | User registration |
| `/login` | GET, POST | Public | User authentication & multi-modal signal capture |
| `/dashboard` | GET | Authenticated | User dashboard with live Risk Explanation UI |
| `/logout` | GET | Authenticated | Session termination |
| `/api/behavior/keystroke` | POST | Authenticated | Record aggregate keystroke dynamics features |
| `/api/behavior/mouse` | POST | Authenticated | Record aggregate mouse movement features |
| `/api/baseline` | GET | Authenticated | Retrieve current user's rolling behavioural baseline |
| `/api/risk/latest` | GET | Authenticated | Retrieve current user's latest risk evaluation & explanation |
