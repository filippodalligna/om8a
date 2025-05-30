from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models.models import User, user_follows
from app.services.stats_service import get_user_stats # Added import

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/<int:user_id>/follow', methods=['POST'])
@login_required
def follow_user(user_id):
    user_to_follow = User.query.get_or_404(user_id)

    if user_to_follow.id == current_user.id:
        return jsonify({'error': _("You cannot follow yourself.")}), 400

    # Check if already following: current_user.followed is a list of User objects
    # The filter for the 'followed' relationship checks the right side of the relationship
    # (the users that current_user is following).
    # So, we filter if user_to_follow is already in current_user.followed.
    # Using .filter(User.id == user_to_follow.id) is more explicit on the relationship target.
    if current_user.followed.filter(user_follows.c.followed_id == user_to_follow.id).count() > 0:
        return jsonify({'message': _("You are already following this user.")}), 400

    current_user.followed.append(user_to_follow)
    db.session.commit()
    return jsonify({'message': _("You are now following %(username)s.", username=user_to_follow.username)}), 200

@users_bp.route('/<int:user_id>/follow', methods=['DELETE']) # Note: Same route, different method
@login_required
def unfollow_user(user_id):
    user_to_unfollow = User.query.get_or_404(user_id)

    if current_user.followed.filter(user_follows.c.followed_id == user_to_unfollow.id).count() == 0:
        return jsonify({'message': _("You are not following this user.")}), 400

    current_user.followed.remove(user_to_unfollow)
    db.session.commit()
    return jsonify({'message': _("You have unfollowed %(username)s.", username=user_to_unfollow.username)}), 200

@users_bp.route('/<int:user_id>/followers', methods=['GET'])
def get_user_followers(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # 'user.followers' is the dynamic backref from the 'followed' relationship
    followers_pagination = user.followers.paginate(page=page, per_page=per_page, error_out=False)
    followers_data = [{'id': u.id, 'username': u.username} for u in followers_pagination.items]

    return jsonify({
        'followers': followers_data,
        'total': followers_pagination.total,
        'pages': followers_pagination.pages,
        'current_page': followers_pagination.page
    }), 200

@users_bp.route('/<int:user_id>/following', methods=['GET'])
def get_user_following(user_id):
    user = User.query.get_or_404(user_id)
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    # 'user.followed' is the relationship representing users this 'user' is following
    followed_pagination = user.followed.paginate(page=page, per_page=per_page, error_out=False)
    followed_data = [{'id': u.id, 'username': u.username} for u in followed_pagination.items]

    return jsonify({
        'following': followed_data,
        'total': followed_pagination.total,
        'pages': followed_pagination.pages,
        'current_page': followed_pagination.page
    }), 200

@users_bp.route('/<int:user_id>/stats', methods=['GET'])
@login_required
def get_user_statistics(user_id):
    # Allow user to see their own stats, or admin to see anyone's
    if not current_user.is_admin and current_user.id != user_id:
        return jsonify({'error': _('You are not authorized to view these statistics.')}), 403

    stats = get_user_stats(user_id)
    if stats is None: # User not found by service
        return jsonify({'error': _('User not found.')}), 404
    return jsonify(stats), 200
