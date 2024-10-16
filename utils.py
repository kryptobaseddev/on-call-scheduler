from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask import jsonify, current_app
from models import User
from flask_login import current_user

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(msg='Authentication required'), 401
        if current_user.role != 'admin':
            return jsonify(msg='Admin access required'), 403
        return fn(*args, **kwargs)
    return wrapper

def manager_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify(msg='Authentication required'), 401
        if current_user.role != 'manager':
            return jsonify(msg='Manager access required'), 403
        return fn(*args, **kwargs)
    return wrapper
