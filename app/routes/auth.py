from flask import Blueprint, render_template, request, redirect, url_for, session, flash, g
from functools import wraps
from typing import Optional, Dict, Any, Callable
from app.models.user import (
    create_user,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    verify_user_password
)

auth = Blueprint('auth', __name__)

def get_current_user() -> Optional[Dict[str, Any]]:
    """Helper to retrieve current authenticated user dict from session."""
    user_id = session.get('user_id')
    if user_id is None:
        return None
    if 'current_user' not in g:
        g.current_user = get_user_by_id(user_id)
    return g.current_user

def login_required(f: Callable) -> Callable:
    """Decorator to enforce authentication on protected endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if get_current_user() is None:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

@auth.route('/register', methods=['GET', 'POST'])
def register():
    """User registration route."""
    if get_current_user():
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Input Validation
        if not username:
            flash("Username is required.", "danger")
            return render_template('register.html', username=username, email=email), 400

        if not email:
            flash("Email is required.", "danger")
            return render_template('register.html', username=username, email=email), 400

        if not password:
            flash("Password is required.", "danger")
            return render_template('register.html', username=username, email=email), 400

        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template('register.html', username=username, email=email), 400

        if get_user_by_username(username):
            flash("Username is already taken.", "danger")
            return render_template('register.html', username=username, email=email), 400

        if get_user_by_email(email):
            flash("Email is already registered.", "danger")
            return render_template('register.html', username=username, email=email), 400

        # Create user
        user = create_user(username, email, password)
        if user:
            flash("Registration successful! Please log in.", "success")
            return redirect(url_for('auth.login'))
        else:
            flash("An error occurred during registration. Please try again.", "danger")
            return render_template('register.html', username=username, email=email), 500

    return render_template('register.html')

@auth.route('/login', methods=['GET', 'POST'])
def login():
    """User login route."""
    if get_current_user():
        return redirect(url_for('auth.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash("Invalid username or password.", "danger")
            return render_template('login.html', username=username), 400

        user = get_user_by_username(username)
        if not user or not verify_user_password(user, password):
            # Generic error message to prevent username enumeration
            flash("Invalid username or password.", "danger")
            return render_template('login.html', username=username), 401

        # Step 3: Parse optional keystroke features
        ks_data = None
        keystroke_json = request.form.get('keystroke_data')
        if keystroke_json:
            try:
                import json
                from app.models.keystroke import validate_keystroke_features, save_keystroke_features
                parsed_ks = json.loads(keystroke_json)
                is_valid, _ = validate_keystroke_features(parsed_ks)
                if is_valid:
                    save_keystroke_features(user['id'], parsed_ks)
                    ks_data = parsed_ks
            except Exception:
                pass

        # Step 4: Parse optional mouse features
        ms_data = None
        mouse_json = request.form.get('mouse_data')
        if mouse_json:
            try:
                import json
                from app.models.mouse import validate_mouse_features, save_mouse_features
                parsed_ms = json.loads(mouse_json)
                is_valid, _ = validate_mouse_features(parsed_ms)
                if is_valid and parsed_ms.get('sample_available') is not False:
                    save_mouse_features(user['id'], parsed_ms)
                    ms_data = parsed_ms
            except Exception:
                pass

        # Step 5: Collect and evaluate contextual login signals
        context_eval = None
        try:
            from datetime import datetime
            from app.services.context_service import (
                get_client_ip, get_location_from_ip, generate_device_id, evaluate_context_signals
            )
            from app.models.context import save_context_features, get_user_context_features

            client_ip = get_client_ip(request)
            location = get_location_from_ip(client_ip)
            device_id = generate_device_id(request)
            login_time = datetime.now()

            historical_context = get_user_context_features(user['id'])
            context_eval = evaluate_context_signals(
                user_id=user['id'],
                current_device_id=device_id,
                current_ip=client_ip,
                current_location=location,
                current_login_time=login_time,
                historical_samples=historical_context
            )
            save_context_features(context_eval)
        except Exception:
            pass

        # Step 7 & 8: Calculate Risk Score and generate Explanation
        risk_eval = None
        try:
            from app.risk_engine.scoring import evaluate_login_risk
            from app.models.risk import save_risk_score
            risk_eval = evaluate_login_risk(
                user_id=user['id'],
                current_keystroke=ks_data,
                current_mouse=ms_data,
                context_eval=context_eval
            )
            save_risk_score(user['id'], risk_eval)
        except Exception:
            pass

        # Step 9: Decision Engine - evaluate risk thresholds for step-up OTP
        from app.risk_engine.decision import evaluate_risk_decision, ACTION_STEP_UP_OTP
        decision = evaluate_risk_decision(risk_eval)

        if decision.get('action') == ACTION_STEP_UP_OTP:
            # Elevated risk triggers Step-Up OTP Verification
            from app.services.otp_service import generate_otp_for_user
            otp_code = generate_otp_for_user(user['id'])

            session.clear()
            session['pending_user_id'] = user['id']
            session['pending_risk_decision'] = decision
            session['pending_risk_explanation'] = risk_eval.get('explanation') if risk_eval else {}
            session['demo_otp'] = otp_code  # Stored for dev/demo display helper

            flash("Unusual login activity detected. Please complete step-up verification.", "warning")
            return redirect(url_for('auth.verify_otp'))

        # Low risk or initial profile: authenticate session directly
        session.clear()
        session['user_id'] = user['id']

        # Step 6: Recalculate rolling rate-capped behavioural baseline
        try:
            from app.services.baseline_service import create_or_update_user_baseline
            create_or_update_user_baseline(user['id'])
        except Exception:
            pass

        return redirect(url_for('auth.dashboard'))

    return render_template('login.html')

@auth.route('/verify-otp', methods=['GET', 'POST'])
def verify_otp():
    """Step-Up OTP Verification route for elevated risk logins."""
    pending_user_id = session.get('pending_user_id')
    if not pending_user_id:
        flash("No pending verification session. Please log in.", "warning")
        return redirect(url_for('auth.login'))

    user = get_user_by_id(pending_user_id)
    if not user:
        session.clear()
        return redirect(url_for('auth.login'))

    decision = session.get('pending_risk_decision', {})
    explanation = session.get('pending_risk_explanation', {})
    demo_otp = session.get('demo_otp')

    if request.method == 'POST':
        otp_code = request.form.get('otp_code', '').strip()
        from app.services.otp_service import verify_user_otp
        is_valid, msg = verify_user_otp(pending_user_id, otp_code)

        if is_valid:
            # Step-up verification succeeded: authenticate user session
            session.clear()
            session['user_id'] = user['id']

            # Update baseline safely after successful multi-factor verification
            try:
                from app.services.baseline_service import create_or_update_user_baseline
                create_or_update_user_baseline(user['id'])
            except Exception:
                pass

            flash("Identity verified successfully. Welcome to your dashboard!", "success")
            return redirect(url_for('auth.dashboard'))
        else:
            flash(msg, "danger")
            return render_template(
                'otp_verify.html',
                user=user,
                decision=decision,
                explanation=explanation,
                demo_otp=demo_otp
            ), 400

    return render_template(
        'otp_verify.html',
        user=user,
        decision=decision,
        explanation=explanation,
        demo_otp=demo_otp
    )

@auth.route('/resend-otp', methods=['POST'])
def resend_otp():
    """Resend a new OTP verification code."""
    pending_user_id = session.get('pending_user_id')
    if not pending_user_id:
        flash("No pending verification session.", "warning")
        return redirect(url_for('auth.login'))

    from app.services.otp_service import generate_otp_for_user
    otp_code = generate_otp_for_user(pending_user_id)
    session['demo_otp'] = otp_code
    flash("A new verification code has been sent.", "info")
    return redirect(url_for('auth.verify_otp'))


@auth.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    """Protected user dashboard route."""
    current_user = get_current_user()
    from app.models.risk import get_latest_user_risk_score
    latest_risk = get_latest_user_risk_score(current_user['id'])
    return render_template('dashboard.html', user=current_user, risk=latest_risk)

@auth.route('/logout', methods=['GET'])
def logout():
    """User logout route."""
    session.clear()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for('auth.login'))
