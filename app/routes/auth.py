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

        # Successful login: set session
        session.clear()
        session['user_id'] = user['id']

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

        # Step 7: Calculate Risk Score for current login attempt against user baseline
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
            # Risk calculation error must not block user login access
            pass

        # Step 6: Recalculate rolling behavioural baseline for authenticated user
        try:
            from app.services.baseline_service import create_or_update_user_baseline
            create_or_update_user_baseline(user['id'])
        except Exception:
            # Baseline update error must not block user login access
            pass

        return redirect(url_for('auth.dashboard'))

    return render_template('login.html')

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
