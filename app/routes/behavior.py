from flask import Blueprint, request, jsonify, session
from app.routes.auth import get_current_user
from app.models.keystroke import validate_keystroke_features, save_keystroke_features
from app.models.mouse import validate_mouse_features, save_mouse_features
from app.services.baseline_service import create_or_update_user_baseline, get_user_baseline

behavior = Blueprint('behavior', __name__)

@behavior.route('/api/behavior/keystroke', methods=['POST'])
def store_keystroke_features():
    """
    API endpoint to accept and validate non-sensitive aggregate keystroke timing features.
    Saves features linked to the currently authenticated user session.
    """
    user = get_current_user()
    if not user:
        return jsonify({
            "status": "error",
            "message": "Authentication required to record behavioural features."
        }), 401

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            "status": "error",
            "message": "Invalid or missing JSON payload."
        }), 400

    is_valid, error_msg = validate_keystroke_features(data)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": f"Validation failed: {error_msg}"
        }), 400

    try:
        sample_id = save_keystroke_features(user['id'], data)
        # Update rolling baseline automatically
        create_or_update_user_baseline(user['id'])
        return jsonify({
            "status": "success",
            "message": "Keystroke features stored successfully.",
            "sample_id": sample_id
        }), 201
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Failed to store keystroke features in database."
        }), 500

@behavior.route('/api/behavior/mouse', methods=['POST'])
def store_mouse_features():
    """
    API endpoint to accept and validate non-sensitive aggregate mouse movement features.
    Saves features linked to the currently authenticated user session.
    """
    user = get_current_user()
    if not user:
        return jsonify({
            "status": "error",
            "message": "Authentication required to record behavioural features."
        }), 401

    data = request.get_json(silent=True)
    if data is None:
        return jsonify({
            "status": "error",
            "message": "Invalid or missing JSON payload."
        }), 400

    # Handle insufficient mouse movement sample gracefully
    if data.get('sample_available') is False:
        return jsonify({
            "status": "success",
            "message": "No significant mouse movement sample recorded.",
            "sample_stored": False
        }), 200

    is_valid, error_msg = validate_mouse_features(data)
    if not is_valid:
        return jsonify({
            "status": "error",
            "message": f"Validation failed: {error_msg}"
        }), 400

    try:
        sample_id = save_mouse_features(user['id'], data)
        # Update rolling baseline automatically
        create_or_update_user_baseline(user['id'])
        return jsonify({
            "status": "success",
            "message": "Mouse features stored successfully.",
            "sample_id": sample_id
        }), 201
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": "Failed to store mouse features in database."
        }), 500

@behavior.route('/api/baseline', methods=['GET'])
def get_current_user_baseline_endpoint():
    """
    Authenticated debug endpoint to retrieve the current user's rolling behavioural baseline.
    """
    user = get_current_user()
    if not user:
        return jsonify({
            "status": "error",
            "message": "Authentication required to view baseline."
        }), 401

    baseline = get_user_baseline(user['id'])
    return jsonify({
        "status": "success",
        "baseline": baseline
    }), 200

@behavior.route('/api/risk/latest', methods=['GET'])
def get_latest_risk_score_endpoint():
    """
    Authenticated debug endpoint to retrieve the current user's latest risk evaluation score.
    """
    user = get_current_user()
    if not user:
        return jsonify({
            "status": "error",
            "message": "Authentication required to view risk evaluation."
        }), 401

    from app.models.risk import get_latest_user_risk_score
    risk_data = get_latest_user_risk_score(user['id'])
    return jsonify({
        "status": "success",
        "risk_evaluation": risk_data
    }), 200
