from functools import wraps
from flask_login import current_user
from flask import jsonify
from flask_babel import gettext as _

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return jsonify({'error': _('Admin access required.')}), 403 # Forbidden
        return f(*args, **kwargs)
    return decorated_function
