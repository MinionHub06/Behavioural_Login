import sqlite3
from pathlib import Path
from flask import g, current_app

def get_db() -> sqlite3.Connection:
    """
    Get or create a database connection for the current application context.
    Returns sqlite3.Row object factory for dict-like access.
    """
    if 'db' not in g:
        db_path = current_app.config['DATABASE_PATH']
        g.db = sqlite3.connect(
            db_path,
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

def close_db(e=None) -> None:
    """Closes the database connection at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db(app=None) -> None:
    """
    Ensures database directory exists and creates initial schema/tables if needed.
    Modular structure allowing future modules (users, behavioural profiles, etc.)
    to execute their schema migrations cleanly.
    """
    db_path = Path(app.config['DATABASE_PATH'] if app else current_app.config['DATABASE_PATH'])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Establish connection to ensure file and schema are initialized
    conn = sqlite3.connect(str(db_path))
    from app.models.user import create_users_table
    from app.models.keystroke import create_keystroke_features_table
    from app.models.mouse import create_mouse_features_table
    from app.models.context import create_context_features_table
    from app.models.baseline import create_behavioural_baselines_table
    from app.models.risk import create_risk_scores_table
    from app.models.otp import create_otp_table
    create_users_table(conn)
    create_keystroke_features_table(conn)
    create_mouse_features_table(conn)
    create_context_features_table(conn)
    create_behavioural_baselines_table(conn)
    create_risk_scores_table(conn)
    create_otp_table(conn)
    conn.close()

def init_app(app) -> None:
    """Register database teardown and initialize database file."""
    app.teardown_appcontext(close_db)
    init_db(app)
