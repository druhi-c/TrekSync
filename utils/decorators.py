from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user
from models import UserRole

def role_required(role_name):
    """Internal helper to enforce role-based access control."""
    def decorator(f):
        @wraps(f)
        def decorated_view(*args, **kwargs):
            if not current_user.is_authenticated:
                flash("You must be logged in to access this page.", "danger")
                return redirect(url_for("auth.login"))
            if current_user.role != role_name:
                flash(f"Access denied. This page is only accessible to {role_name} users.", "danger")
                return redirect(url_for("auth.login"))
            return f(*args, **kwargs)
        return decorated_view
    return decorator

def admin_required(f):
    return role_required(UserRole.ADMIN.value)(f)

def staff_required(f):
    return role_required(UserRole.STAFF.value)(f)

def trekker_required(f):
    return role_required(UserRole.TREKKER.value)(f)
