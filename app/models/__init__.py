from app.models.base import get_db, close_db, init_db, init_app
from app.models.user import (
    create_user,
    get_user_by_username,
    get_user_by_email,
    get_user_by_id,
    verify_user_password
)
from app.models.keystroke import (
    create_keystroke_features_table,
    validate_keystroke_features,
    save_keystroke_features,
    get_user_keystroke_features
)
from app.models.mouse import (
    create_mouse_features_table,
    validate_mouse_features,
    save_mouse_features,
    get_user_mouse_features
)
from app.models.context import (
    create_context_features_table,
    save_context_features,
    get_user_context_features
)
from app.models.baseline import (
    create_behavioural_baselines_table,
    save_or_update_baseline,
    get_user_baseline_record
)
from app.models.risk import (
    create_risk_scores_table,
    save_risk_score,
    get_latest_user_risk_score
)

__all__ = [
    'get_db', 
    'close_db', 
    'init_db', 
    'init_app',
    'create_user',
    'get_user_by_username',
    'get_user_by_email',
    'get_user_by_id',
    'verify_user_password',
    'create_keystroke_features_table',
    'validate_keystroke_features',
    'save_keystroke_features',
    'get_user_keystroke_features',
    'create_mouse_features_table',
    'validate_mouse_features',
    'save_mouse_features',
    'get_user_mouse_features',
    'create_context_features_table',
    'save_context_features',
    'get_user_context_features',
    'create_behavioural_baselines_table',
    'save_or_update_baseline',
    'get_user_baseline_record',
    'create_risk_scores_table',
    'save_risk_score',
    'get_latest_user_risk_score'
]
