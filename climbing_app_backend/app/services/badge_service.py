# climbing_app_backend/app/services/badge_service.py
from app.models.models import db, User, Badge, UserBadge, Comment, UserAttempt, ClimbingBlock
from flask_babel import gettext as _
from app.services.notification_service import send_notification # Added

# Define badge name keys (constants)
BADGE_FIRST_COMMENT = "BADGE_FIRST_COMMENT"
BADGE_FIRST_COMPLETED_CLIMB = "BADGE_FIRST_COMPLETED_CLIMB"
BADGE_BLOCK_UPLOADER = "BADGE_BLOCK_UPLOADER"

# Predefined badge details (name key, default display name, default description)
# In a real app, display names and descriptions would come from i18n files using the name key.
# For now, we'll store descriptive names/descriptions directly in the Badge table.
PREDEFINED_BADGES = {
    BADGE_FIRST_COMMENT: {"name": "Commentator", "description": "Awarded for posting your first comment.", "icon_url": "/static/badges/commentator.png", "criteria": "Post 1 comment."},
    BADGE_FIRST_COMPLETED_CLIMB: {"name": "First Summit", "description": "Awarded for recording your first completed climb.", "icon_url": "/static/badges/first_summit.png", "criteria": "Complete 1 climb."},
    BADGE_BLOCK_UPLOADER: {"name": "Route Setter", "description": "Awarded for uploading your first climbing block with a photo.", "icon_url": "/static/badges/route_setter.png", "criteria": "Upload 1 block with photo."},
}

def _ensure_badge_exists(badge_key):
    """Ensures a badge exists in the DB, creating it if necessary."""
    badge_details = PREDEFINED_BADGES.get(badge_key)
    if not badge_details:
        # This case should ideally not happen if badge_key is always one of the constants
        print(f"Warning: Badge key {badge_key} not predefined.") # Or raise error
        return None

    badge = Badge.query.filter_by(name=badge_details["name"]).first() # Check by the display name for now
    if not badge:
        print(f"Creating badge: {badge_details['name']}")
        badge = Badge(
            name=badge_details["name"], # Using the display name as the unique name key for now
            description=badge_details["description"],
            icon_url=badge_details["icon_url"],
            criteria=badge_details["criteria"]
        )
        db.session.add(badge)
        db.session.commit() # Commit here to get badge.id if needed immediately, or commit in award_badge
    return badge

def award_badge(user_id, badge_key):
    """
    Awards a badge to a user if they haven't earned it already.
    Ensures the badge definition exists.
    Returns True if a new badge was awarded, False otherwise.
    """
    user = User.query.get(user_id)
    if not user:
        return False # Should not happen if user_id comes from current_user

    badge = _ensure_badge_exists(badge_key)
    if not badge:
        return False # Badge definition issue

    # Check if user already has this badge
    existing_user_badge = UserBadge.query.filter_by(user_id=user.id, badge_id=badge.id).first()
    if existing_user_badge:
        return False # Already earned

    # Award the badge
    user_badge = UserBadge(user_id=user.id, badge_id=badge.id)
    db.session.add(user_badge)
    db.session.commit() 
    print(f"Awarded badge '{badge.name}' to user {user.id}") # For logging

    # Placeholder for sending a notification about the new badge
    try:
        # Assuming badge.name is the direct display name (e.g., "Commentator")
        # If badge.name were a translation key, _(badge.name) would fetch the translation.
        # For now, we'll assume it's already a displayable string.
        badge_display_name = badge.name 
        payload = {
            "title": _("New Badge Earned!"),
            "body": _("You've earned the '%(badge_name)s' badge.", badge_name=badge_display_name),
            "url": "/profile/badges" # Example URL, adjust as needed for frontend
        }
        send_notification(user, payload)
    except Exception as e:
        # Log error, but don't let notification failure break badge awarding
        print(f"Error trying to send badge notification for user {user.id}, badge {badge.name}: {e}") 
    
    return True
