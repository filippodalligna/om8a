from flask import Blueprint, request, jsonify
from flask_babel import gettext as _ # For potential future i18n of badge names/descriptions
from app import db
from app.models.models import Badge, UserBadge, User

badges_bp = Blueprint('badges', __name__, url_prefix='/badges')

@badges_bp.route('/', methods=['GET'])
def list_all_badges():
    badges = Badge.query.order_by(Badge.name).all()
    badges_data = []
    for badge in badges:
        # Assuming badge.name and badge.description are stored in the default language (e.g., Italian)
        # _() is used here as a placeholder; for these to be translated, they'd need to be keys
        # or full strings present in .po files. For now, they'll return as-is from DB.
        badges_data.append({
            'id': badge.id,
            'name': badge.name, # Using _(badge.name) would require badge.name to be a key
            'description': badge.description, # Same for _(badge.description)
            'icon_url': badge.icon_url,
            'criteria': badge.criteria
        })
    return jsonify(badges_data), 200

@badges_bp.route('/users/<int:user_id>/badges', methods=['GET'])
def get_user_earned_badges(user_id):
    user = User.query.get_or_404(user_id)
    
    # UserBadge objects for the user, ordered by when they were earned
    # user.earned_badges_assoc is the backref from UserBadge.user relationship
    user_badge_associations = user.earned_badges_assoc.order_by(UserBadge.earned_at.desc()).all()
    
    earned_badges_data = []
    for ub_assoc in user_badge_associations:
        badge = ub_assoc.badge # Get the actual Badge object from the association
        earned_badges_data.append({
            'badge_id': badge.id,
            'name': badge.name, # Using _(badge.name) would require badge.name to be a key
            'description': badge.description, # Same for _(badge.description)
            'icon_url': badge.icon_url,
            'earned_at': ub_assoc.earned_at.isoformat() + 'Z' # ISO 8601 format
        })
        
    return jsonify(earned_badges_data), 200
