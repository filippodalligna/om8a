from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.models import User

bp = Blueprint('auth', __name__)

@bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('username') or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing username, email, or password'}), 400

    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if User.query.filter_by(username=username).first():
        return jsonify({'message': 'Username already exists'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'message': 'Email already exists'}), 409

    user = User(username=username, email=email)
    user.set_password(password)  # Uses the method from UserMixin/User model
    db.session.add(user)
    db.session.commit()

    return jsonify({'message': 'User registered successfully'}), 201

@bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or (not data.get('email') and not data.get('username')) or not data.get('password'):
        return jsonify({'message': 'Missing email/username or password'}), 400

    password = data.get('password')
    user = None
    if data.get('email'):
        user = User.query.filter_by(email=data.get('email')).first()
    elif data.get('username'): # Added username login option for flexibility
        user = User.query.filter_by(username=data.get('username')).first()

    if user and user.check_password(password):
        login_user(user)
        return jsonify({
            'message': 'Login successful',
            'user': {'id': user.id, 'username': user.username, 'email': user.email}
        }), 200
    
    return jsonify({'message': 'Invalid credentials'}), 401

@bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logout successful'}), 200

@bp.route('/status', methods=['GET'])
@login_required
def status():
    return jsonify({
        'user_id': current_user.id,
        'username': current_user.username,
        'email': current_user.email
    }), 200

# Placeholder ping route from initial setup, can be removed or kept for basic testing
@bp.route('/ping', methods=['GET'])
def ping():
    return jsonify({'message': 'Auth blueprint is active'})
