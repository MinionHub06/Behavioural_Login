from flask import Blueprint, render_template, request, jsonify
from app.services.evaluation_service import (
    run_comprehensive_evaluation,
    run_slow_mimicry_simulation
)

eval_bp = Blueprint('evaluation', __name__)

@eval_bp.route('/evaluation', methods=['GET'])
def evaluation_dashboard():
    """Renders the comprehensive cybersecurity evaluation and attack simulation dashboard."""
    # Pre-generate standard academic evaluation dataset
    results = run_comprehensive_evaluation(n_genuine=50, n_bot_attacks=50, n_mimicry_attacks=25)
    return render_template('evaluation.html', results=results)

@eval_bp.route('/api/evaluation/run', methods=['POST'])
def run_evaluation_api():
    """API endpoint to run live simulations on demand with custom parameters."""
    data = request.get_json(silent=True) or {}
    try:
        n_gen = int(data.get('n_genuine', 50))
        n_bot = int(data.get('n_bot_attacks', 50))
        n_mimic = int(data.get('n_mimicry_attacks', 25))
    except (ValueError, TypeError):
        n_gen, n_bot, n_mimic = 50, 50, 25

    results = run_comprehensive_evaluation(
        n_genuine=min(200, max(10, n_gen)),
        n_bot_attacks=min(200, max(10, n_bot)),
        n_mimicry_attacks=min(100, max(5, n_mimic))
    )
    return jsonify(results), 200

@eval_bp.route('/api/evaluation/mimicry', methods=['POST'])
def run_mimicry_api():
    """API endpoint to run slow mimicry drift cap experiment."""
    data = request.get_json(silent=True) or {}
    try:
        steps = int(data.get('steps', 15))
        max_drift = float(data.get('max_drift_rate', 0.10))
    except (ValueError, TypeError):
        steps, max_drift = 15, 0.10

    mimic_results = run_slow_mimicry_simulation(
        steps=min(50, max(5, steps)),
        max_drift_rate=min(0.5, max(0.01, max_drift))
    )
    return jsonify(mimic_results), 200
