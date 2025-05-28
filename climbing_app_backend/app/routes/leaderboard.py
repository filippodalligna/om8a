from flask import Blueprint, request, jsonify
from sqlalchemy import func
from app import db
from app.models.models import UserAttempt, User, ClimbingBlock
from datetime import datetime, timedelta

# Define the blueprint
bp = Blueprint('leaderboard', __name__, url_prefix='/leaderboard')

@bp.route('/', methods=['GET'])
def get_leaderboard():
    difficulty = request.args.get('difficulty')
    period = request.args.get('period', 'all_time') # Default to 'all_time'

    # Start with a base query: User.id, User.username, count of completed attempts
    query = db.session.query(
        User.id,
        User.username,
        func.count(UserAttempt.id).label('completed_count')
    )

    # Join UserAttempt with User
    query = query.join(User, User.id == UserAttempt.user_id)

    # Always filter by status == 'completed'
    query = query.filter(UserAttempt.status == 'completed')

    # Apply period filter
    if period == 'weekly':
        start_date = datetime.utcnow() - timedelta(days=7)
        query = query.filter(UserAttempt.recorded_at >= start_date)
    elif period == 'monthly':
        # Approximate as 30 days for simplicity
        start_date = datetime.utcnow() - timedelta(days=30)
        query = query.filter(UserAttempt.recorded_at >= start_date)
    elif period != 'all_time':
        return jsonify({'message': "Invalid period. Use 'weekly', 'monthly', or 'all_time'."}), 400
    
    # Apply difficulty filter
    # This join is only added if a difficulty filter is present.
    if difficulty:
        query = query.join(ClimbingBlock, ClimbingBlock.id == UserAttempt.block_id)
        query = query.filter(ClimbingBlock.difficulty == difficulty)

    # Group by user
    query = query.group_by(User.id, User.username)

    # Order by completed_count descending
    # Using .label('completed_count') means we can order by that label directly
    query = query.order_by(func.count(UserAttempt.id).desc()) # Or query.order_by(db.desc('completed_count'))

    # Limit results (e.g., top 100)
    query = query.limit(100)

    # Execute query
    results = query.all()

    # Serialize results
    leaderboard_data = []
    for r in results:
        leaderboard_data.append({
            'user_id': r.id,
            'username': r.username,
            'completed_count': r.completed_count
        })

    return jsonify(leaderboard_data), 200

# Placeholder ping route from initial setup, can be removed or kept for basic testing
@bp.route('/ping_leaderboard_bp', methods=['GET']) # Renamed to avoid conflict
def ping():
    return jsonify({'message': 'Leaderboard blueprint is active'})
