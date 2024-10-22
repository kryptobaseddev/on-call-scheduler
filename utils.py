from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import jsonify, current_app, abort
from flask_login import current_user
import logging
from datetime import datetime, timezone
import pytz

logger = logging.getLogger(__name__)

def permission_required(permission_name):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated or not current_user.has_permission(permission_name):
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            logger.warning(f"Unauthenticated user attempting to access admin-only function")
            return jsonify(msg='Authentication required'), 401
        if current_user.role != 'admin':
            logger.warning(f"User {current_user.username} with role {current_user.role} denied access to admin-only function")
            return jsonify(msg='Admin access required'), 403
        return fn(*args, **kwargs)
    return wrapper

def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        logger.info(f"User {current_user.username} (role: {current_user.role}) attempting to access manager-only function")
        if not current_user.is_authenticated:
            logger.warning(f"Unauthenticated user attempting to access manager-only function")
            return jsonify(msg='Authentication required'), 401
        if current_user.role not in ['manager', 'admin']:
            logger.warning(f"User {current_user.username} with role {current_user.role} denied access to manager-only function")
            return jsonify(msg='Manager or admin access required'), 403
        logger.info(f"User {current_user.username} granted access to manager-only function")
        return fn(*args, **kwargs)
    return wrapper

def get_user_local_time(user):
    utc_time = datetime.now(timezone.utc)
    user_tz = pytz.timezone(user.timezone)
    return utc_time.astimezone(user_tz)
