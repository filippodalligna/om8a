from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models.models import UserAttempt, User, ClimbingBlock

# Define the blueprint
bp = Blueprint('history', __name__, url_prefix='/history') # url_prefix is defined here

@bp.route('/attempts', methods=['POST'])
@login_required
def log_attempt():
    data = request.get_json()
    if not data:
        return jsonify({'message': 'No input data provided'}), 400

    required_fields = ['block_id', 'status']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400

    block_id = data.get('block_id')
    status = data.get('status')

    if not isinstance(block_id, int):
         return jsonify({'message': 'block_id must be an integer'}), 400
        
    if status not in ['tried', 'completed']:
        return jsonify({'message': "Invalid status value. Must be 'tried' or 'completed'."}), 400

    block = ClimbingBlock.query.get(block_id)
    if not block:
        return jsonify({'message': 'Climbing block not found'}), 404

    new_attempt = UserAttempt(
        user_id=current_user.id,
        block_id=block_id,
        status=status,
        attempts_count=data.get('attempts_count'),
        time_taken=data.get('time_taken'),
        sensations=data.get('sensations'),
        personal_notes=data.get('personal_notes')
    )

    db.session.add(new_attempt)
    db.session.commit()
    
    attempt_data = {
        'id': new_attempt.id,
        'user_id': new_attempt.user_id,
        'block_id': new_attempt.block_id,
        'status': new_attempt.status,
        'attempts_count': new_attempt.attempts_count,
        'time_taken': new_attempt.time_taken,
        'sensations': new_attempt.sensations,
        'personal_notes': new_attempt.personal_notes,
        'recorded_at': new_attempt.recorded_at.isoformat(),
        'block_details': {
            'name': block.name,
            'difficulty': block.difficulty
        }
    }
    return jsonify({'message': 'Attempt logged successfully', 'attempt': attempt_data}), 201

@bp.route('/me', methods=['GET'])
@login_required
def get_my_history():
    attempts = UserAttempt.query.filter_by(user_id=current_user.id).order_by(UserAttempt.recorded_at.desc()).all()
    
    attempts_data = []
    for attempt in attempts:
        block = ClimbingBlock.query.get(attempt.block_id) # Query block for details
        attempts_data.append({
            'id': attempt.id,
            'block_id': attempt.block_id,
            'block_name': block.name if block else 'Unknown',
            'block_difficulty': block.difficulty if block else 'Unknown',
            'status': attempt.status,
            'attempts_count': attempt.attempts_count,
            'time_taken': attempt.time_taken,
            'sensations': attempt.sensations,
            'personal_notes': attempt.personal_notes,
            'recorded_at': attempt.recorded_at.isoformat()
        })
    return jsonify(attempts_data), 200

@bp.route('/user/<int:user_id>', methods=['GET'])
def get_user_history(user_id):
    # Check if user exists
    user = User.query.get(user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Query only 'completed' attempts for the specified user_id
    attempts = UserAttempt.query.filter_by(user_id=user_id, status='completed') \
                                .order_by(UserAttempt.recorded_at.desc()).all()
    
    attempts_data = []
    for attempt in attempts:
        block = ClimbingBlock.query.get(attempt.block_id) # Query block for details
        attempts_data.append({
            'id': attempt.id, # For MVP, including ID is fine.
            'block_id': attempt.block_id,
            'block_name': block.name if block else 'Unknown',
            'block_difficulty': block.difficulty if block else 'Unknown',
            'status': attempt.status, # Will always be 'completed' due to query filter
            # Optional fields might be excluded for public view depending on privacy rules
            # 'attempts_count': attempt.attempts_count, 
            # 'time_taken': attempt.time_taken,
            # 'sensations': attempt.sensations,
            # 'personal_notes': attempt.personal_notes,
            'recorded_at': attempt.recorded_at.isoformat()
        })
    return jsonify(attempts_data), 200

# Placeholder ping route from initial setup, can be removed or kept for basic testing
@bp.route('/ping_history_bp', methods=['GET']) # Renamed to avoid conflict
def ping():
    return jsonify({'message': 'History blueprint is active'})
