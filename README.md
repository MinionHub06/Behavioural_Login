# Behavioural Login Verification System

## Short Description
A Cyber Security academic project implementing continuous user authentication using **Keystroke Dynamics**, **Mouse Movement kinetics**, and **Contextual Risk Signals** to calculate adaptive risk scores, resist adversarial slow mimicry attacks via **Rate-Capped Drift Adaptation**, and trigger **Step-Up OTP Verification** with transparent explainable AI attributions.

## Implementation Status
- **Step 1: Flask Project Foundation** - COMPLETE
- **Step 2: Basic Conventional Authentication** - COMPLETE
- **Step 3: Keystroke Dynamics Capture & Feature Extraction** - COMPLETE
- **Step 4: Mouse Movement Dynamics Capture & Feature Extraction** - COMPLETE
- **Step 5: Contextual Login Signals (Device, Location, Time)** - COMPLETE
- **Step 6: Per-User Rolling Behavioural Baseline** - COMPLETE
- **Step 7: Risk Scoring Engine** - COMPLETE
- **Step 8: Explainable Risk Score / Explanation Module** - COMPLETE
- **Step 9: Risk-Based Decision Engine & Adaptive Thresholds** - COMPLETE
- **Step 10: Step-Up Verification (OTP Flow & Resend Mechanism)** - COMPLETE
- **Step 11: Rate-Capped (Drift-Capped) Baseline Adaptation Engine** - COMPLETE
- **Step 12: Attack Simulation & Comprehensive Evaluation Suite** - COMPLETE

---

## Step 9 - Risk-Based Decision Engine
Evaluates normalized composite risk against configurable thresholds (`RISK_THRESHOLD_LOW = 0.35`, `RISK_THRESHOLD_HIGH = 0.50`):
- **Normal / Low Risk (`< 0.50`)**: Authenticates immediately with zero friction.
- **Initial Profile (`insufficient_baseline`)**: Grants access seamlessly while establishing user baseline.
- **Elevated / High Risk (`>= 0.50`)**: Enforces Step-Up verification with explicit reason and signal attribution.

---

## Step 10 - Step-Up OTP Verification
- Generates cryptographically secure 6-digit OTP codes with 5-minute expiry (`OTP_EXPIRY_SECONDS = 300`).
- Enforces a 3-attempt failure lockout (`OTP_MAX_ATTEMPTS = 3`).
- Provides clean `/verify-otp` and `/resend-otp` endpoints with detailed risk explanation triggers and dev demo helper.
- Only upon successful verification is the session fully authenticated and the user baseline updated.

---

## Step 11 - Rate-Capped (Drift-Capped) Baseline Adaptation
- Prevents **Adversarial Slow Mimicry Attacks** where an attacker repeatedly logs in with slight behavioral variations to poison the baseline.
- Capped maximum drift per update cycle:
  $$\text{bounded\_val} = \text{clamp}\Big(\text{candidate\_val}, \;\text{prev\_val} \times (1 - \delta), \;\text{prev\_val} \times (1 + \delta)\Big) \quad (\delta = 0.10)$$
- Preserves legitimate long-term behavioral aging while suppressing attacker mimicry attempts.

---

## Step 12 - Attack Simulation & Academic Evaluation Suite
Compares 4 system paradigms across genuine logins, automated bot attacks, and slow mimicry attacks:
1. **Proposed Multi-Modal System** (Keystroke + Mouse + Context + Drift Cap + Explainable AI)
2. **Standard Password + CAPTCHA Baseline**
3. **Multi-Modal System Without Drift Cap** (Vulnerable to baseline poisoning)
4. **Multi-Modal System Without Explanation Layer** (Black-box single score)

### Evaluation Metrics
- **Detection Accuracy**: Overall classification accuracy across all login attempts.
- **False Acceptance Rate (FAR)**: Percentage of attacker/bot logins incorrectly admitted.
- **False Rejection Rate (FRR)**: Percentage of legitimate users falsely triggered for step-up.
- **Explainability Attribution Accuracy**: Frequency of correct dominant signal identification.
- **Drift-Resistance**: Maintained risk elevation over multi-attempt mimicry sequences.

---

## Project Structure
```text
cybersec-project/
│
├── app/
│   ├── __init__.py          # Application Factory (Blueprint & error handler init)
│   ├── config.py            # Risk weights, thresholds, drift rate & OTP config
│   │
│   ├── routes/
│   │   ├── __init__.py      # Blueprint exports
│   │   ├── main.py          # Status & health routes (/, /health)
│   │   ├── auth.py          # Auth routes (/register, /login, /verify-otp, /resend-otp, /dashboard, /logout)
│   │   ├── behavior.py      # API routes (/api/behavior/*, GET /api/baseline, GET /api/risk/latest)
│   │   └── evaluation.py    # Evaluation portal (/evaluation, /api/evaluation/run, /api/evaluation/mimicry)
│   │
│   ├── models/
│   │   ├── __init__.py      # DB helper exports
│   │   ├── base.py          # SQLite connection and DB table creation hook
│   │   ├── user.py          # User model & SQL CRUD queries
│   │   ├── keystroke.py     # Keystroke features schema & persistence
│   │   ├── mouse.py         # Mouse features schema & persistence
│   │   ├── context.py       # Context features schema & persistence
│   │   ├── baseline.py      # Behavioural baseline schema & persistence
│   │   ├── risk.py          # Risk evaluation & explanation schema/persistence
│   │   └── otp.py           # Step-up OTP schema, validation & attempt tracking
│   │
│   ├── services/
│   │   ├── __init__.py          # Service exports
│   │   ├── context_service.py   # Context evaluation service
│   │   ├── baseline_service.py  # Recency-weighted & rate-capped baseline engine
│   │   ├── otp_service.py       # Secure OTP generation, validation & lockout service
│   │   └── evaluation_service.py# Synthetic attack generators & benchmark engine
│   │
│   ├── risk_engine/
│   │   ├── __init__.py      # Risk engine exports
│   │   ├── scoring.py       # Distance-from-baseline risk engine
│   │   ├── explanation.py   # Explainable risk feature attribution module
│   │   └── decision.py      # Adaptive threshold & step-up decision engine
│   │
│   ├── templates/
│   │   ├── index.html       # System status page with quick navigation
│   │   ├── register.html    # Registration page
│   │   ├── login.html       # Login page (with multi-modal capture)
│   │   ├── otp_verify.html  # Step-up OTP verification screen with risk trigger
│   │   ├── dashboard.html   # Authenticated user dashboard with Risk Explanation UI
│   │   └── evaluation.html  # Interactive cybersecurity evaluation benchmark portal
│   │
│   └── static/
│       ├── css/
│       │   └── style.css    # Dark theme CSS
│       └── js/
│           ├── main.js      # Frontend health check script
│           ├── keystroke.js # Client-side keystroke timing extraction
│           └── mouse.js     # Client-side mouse dynamics extraction
│
├── tests/
│   ├── test_app.py          # Base Flask & health tests (4 tests)
│   ├── test_auth.py         # Authentication test suite (13 tests)
│   ├── test_behavior.py     # Keystroke dynamics unit tests (8 tests)
│   ├── test_mouse.py        # Mouse dynamics unit tests (11 tests)
│   ├── test_context.py      # Contextual risk signal unit tests (7 tests)
│   ├── test_baseline.py     # Rolling baseline unit tests (7 tests)
│   ├── test_risk.py         # Risk scoring engine unit tests (6 tests)
│   ├── test_explanation.py  # Explanation module unit tests (5 tests)
│   ├── test_decision.py     # Decision engine unit tests (4 tests)
│   ├── test_drift_cap.py    # Rate-capped drift adaptation unit tests (3 tests)
│   ├── test_otp.py          # OTP step-up verification unit tests (4 tests)
│   └── test_evaluation.py   # Simulation & evaluation benchmark unit tests (4 tests)
│
├── evaluate.py              # Academic evaluation CLI script (prints formatted tables)
├── view_db.py               # SQLite database inspector script
├── requirements.txt         # Dependencies
├── run.py                   # Development server execution script
└── README.md                # Full system documentation
```

---

## How to Run Tests
```bash
pytest
```
*Total: 76 automated tests across 12 test suites.*

---

## How to Run Evaluation Benchmark CLI
```bash
python evaluate.py
```

---

## How to Run the Web Application
```bash
python run.py
```
*Access application at: `http://127.0.0.1:5000`*
*Interactive Evaluation Portal at: `http://127.0.0.1:5000/evaluation`*

---

## Available Routes
| Route | Method | Access | Description |
|---|---|---|---|
| `/` | GET | Public | Home / system status page |
| `/health` | GET | Public | JSON health check endpoint |
| `/register` | GET, POST | Public | User registration |
| `/login` | GET, POST | Public | User authentication & multi-modal signal capture |
| `/verify-otp` | GET, POST | Public (Session) | Step-up OTP verification for anomalous logins |
| `/resend-otp` | POST | Public (Session) | Regenerate and resend verification OTP |
| `/dashboard` | GET | Authenticated | User dashboard with live Risk Explanation UI |
| `/evaluation` | GET | Public | Cybersecurity benchmark & attack simulation portal |
| `/api/evaluation/run` | POST | Public | Trigger live benchmark simulation |
| `/api/evaluation/mimicry` | POST | Public | Trigger slow mimicry drift cap experiment |
| `/logout` | GET | Authenticated | Session termination |
| `/api/behavior/keystroke` | POST | Authenticated | Record aggregate keystroke dynamics features |
| `/api/behavior/mouse` | POST | Authenticated | Record aggregate mouse movement features |
| `/api/baseline` | GET | Authenticated | Retrieve current user's rolling behavioural baseline |
| `/api/risk/latest` | GET | Authenticated | Retrieve current user's latest risk evaluation & explanation |
