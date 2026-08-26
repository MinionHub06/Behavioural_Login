from flask import Blueprint, render_template, jsonify, Response
from typing import Tuple

main = Blueprint('main', __name__)

@main.route('/', methods=['GET'])
def index() -> str:
    """Render main home/dashboard status page."""
    return render_template('index.html')

@main.route('/health', methods=['GET'])
def health_check() -> Tuple[Response, int]:
    """Health check endpoint returning JSON status."""
    return jsonify({
        "status": "ok",
        "service": "behavioural-login-verification"
    }), 200
