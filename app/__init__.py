from flask import Flask, jsonify
from typing import Optional, Type
from app.config import Config
from app.models.base import init_app

def create_app(config_class: Type[Config] = Config) -> Flask:
    """
    Application factory for Behavioural Login Verification System.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Database
    init_app(app)

    # Register Blueprints
    from app.routes.main import main as main_blueprint
    from app.routes.auth import auth as auth_blueprint
    from app.routes.behavior import behavior as behavior_blueprint
    app.register_blueprint(main_blueprint, url_prefix='/')
    app.register_blueprint(auth_blueprint, url_prefix='/')
    app.register_blueprint(behavior_blueprint, url_prefix='/')

    # Register Error Handlers
    register_error_handlers(app)

    return app


def register_error_handlers(app: Flask) -> None:
    """Register HTTP error handlers for 404 and 500."""
    
    @app.errorhandler(404)
    def not_found_error(error):
        return jsonify({
            "error": "Not Found",
            "message": "The requested resource was not found on the server.",
            "status_code": 404
        }), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred on the server.",
            "status_code": 500
        }), 500
