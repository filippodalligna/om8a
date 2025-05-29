import json # For handling JSON data
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from flask_babel import gettext as _
from app import db
from app.models.models import PushSubscription, User # User might not be explicitly needed here if using current_user

notifications_bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications_bp.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    subscription_info = request.json
    if not subscription_info or not subscription_info.get('endpoint'):
        return jsonify({'error': _('Invalid subscription data. Endpoint is required.')}), 400

    subscription_json_str = json.dumps(subscription_info)

    # Check if this exact subscription already exists for the user
    existing_sub = PushSubscription.query.filter_by(
        user_id=current_user.id, 
        subscription_json=subscription_json_str
    ).first()

    if existing_sub:
        return jsonify({'message': _('Subscription already exists.')}), 200 # Or 201 if treated as idempotent success

    new_sub = PushSubscription(
        user_id=current_user.id,
        subscription_json=subscription_json_str
    )
    db.session.add(new_sub)
    db.session.commit()

    return jsonify({'message': _('Successfully subscribed to push notifications.')}), 201

@notifications_bp.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    data = request.json
    if not data or not data.get('endpoint'):
        return jsonify({'error': _('Subscription endpoint is required.')}), 400
    
    endpoint_to_remove = data.get('endpoint')

    # Find subscriptions for the current user
    subscriptions = PushSubscription.query.filter_by(user_id=current_user.id).all()
    sub_to_delete = None

    for sub in subscriptions:
        try:
            sub_data = json.loads(sub.subscription_json)
            if sub_data.get('endpoint') == endpoint_to_remove:
                sub_to_delete = sub
                break
        except json.JSONDecodeError:
            # Handle cases where subscription_json is not valid JSON, though ideally it always should be
            # Log this error or handle as appropriate
            continue 

    if sub_to_delete:
        db.session.delete(sub_to_delete)
        db.session.commit()
        return jsonify({'message': _('Successfully unsubscribed from push notifications.')}), 200
    else:
        return jsonify({'error': _('Subscription not found.')}), 404
