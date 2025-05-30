# climbing_app_backend/app/services/notification_service.py
import json
from pywebpush import webpush, WebPushException
from flask import current_app
from app import db # Assuming db is initialized in app.__init__
from app.models.models import PushSubscription, User # User model is needed for preferences
from flask_babel import gettext as _

# Notification Type Constants
NOTIFICATION_TYPE_BADGE_EARNED = "badge_earned"
NOTIFICATION_TYPE_NEW_BLOCK_BY_FOLLOWED = "new_block_by_followed"
NOTIFICATION_TYPE_COMMENT_ON_OWN_BLOCK = "comment_on_own_block"

def send_notification(user, payload_dict, notification_type_key): # New signature
    """
    Sends a push notification to all registered PUSH subscriptions for the given user,
    respecting user's notification preferences.
    payload_dict should be like {"title": "...", "body": "...", "url": "/"}
    notification_type_key is a string constant defining the type of notification.
    """
    # Check user preference for this type of notification first
    if notification_type_key == NOTIFICATION_TYPE_BADGE_EARNED and not user.notify_on_badge_earned:
        print(f"User {user.id} has disabled notifications for badge earned.")
        return
    if notification_type_key == NOTIFICATION_TYPE_NEW_BLOCK_BY_FOLLOWED and not user.notify_on_new_block_by_followed:
        print(f"User {user.id} has disabled notifications for new blocks by followed users.")
        return
    if notification_type_key == NOTIFICATION_TYPE_COMMENT_ON_OWN_BLOCK and not user.notify_on_comment_on_own_block:
        print(f"User {user.id} has disabled notifications for comments on their own blocks.")
        return

    # user.push_subscriptions is the backref from PushSubscription.user
    # Check if there are any active subscriptions
    active_subscriptions = [sub for sub in user.push_subscriptions] # Evaluate the dynamic query
    if not active_subscriptions:
        print(f"No active push subscriptions found for user {user.id}.")
        return

    vapid_private_key = current_app.config.get('VAPID_PRIVATE_KEY')
    vapid_claims = current_app.config.get('VAPID_CLAIMS')

    if not vapid_private_key or "YOUR_GENERATED_PRIVATE_KEY_PLACEHOLDER" in vapid_private_key:
        print("VAPID private key not configured or is a placeholder. Cannot send push notifications.")
        return
    if not vapid_claims: # VAPID_CLAIMS can be just a string (mailto) or a dict
        print("VAPID claims not configured. Cannot send push notifications.")
        return

    # Iterate over a copy of the subscriptions list in case of deletion
    for sub_record in active_subscriptions: # Use the evaluated list
        try:
            subscription_info = json.loads(sub_record.subscription_json)
            payload_json = json.dumps(payload_dict)

            # Ensure VAPID claims is a dictionary
            claims_to_use = vapid_claims.copy() if isinstance(vapid_claims, dict) else {}
            if "sub" not in claims_to_use and isinstance(vapid_claims, str) and "mailto:" in vapid_claims: # Basic check if it's just the mailto string
                 claims_to_use = {"sub": vapid_claims}


            webpush(
                subscription_info=subscription_info,
                data=payload_json,
                vapid_private_key=vapid_private_key,
                vapid_claims=claims_to_use
            )
            print(f"Sent push notification to user {user.id}, endpoint: {subscription_info.get('endpoint')}")
        except WebPushException as ex:
            print(f"WebPushException for user {user.id}, endpoint: {subscription_info.get('endpoint', 'N/A')}: {ex}")
            # Handle common errors, e.g., subscription expired (410 Gone)
            if ex.response and ex.response.status_code == 410:
                print(f"Subscription expired or invalid for user {user.id}, endpoint: {subscription_info.get('endpoint')}. Deleting.")
                db.session.delete(sub_record)
                db.session.commit()
        except json.JSONDecodeError as e:
            print(f"Error decoding subscription_json for user {user.id}, subscription ID {sub_record.id}: {e}. Deleting problematic subscription.")
            db.session.delete(sub_record) # Delete corrupted subscription
            db.session.commit()
        except Exception as e:
            # General exception
            print(f"Error sending push notification to user {user.id}, endpoint: {subscription_info.get('endpoint', 'N/A')}: {e}")
