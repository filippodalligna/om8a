# tests/test_notifications.py
import pytest
import json
from unittest.mock import patch, call # Added
from app.models.models import PushSubscription, User, db, Comment, UserAttempt, ClimbingBlock # Added models
from app.services.badge_service import award_badge, _ensure_badge_exists, BADGE_FIRST_COMMENT, BADGE_BLOCK_UPLOADER, BADGE_FIRST_COMPLETED_CLIMB # Added
from app.services.notification_service import send_notification # For direct testing if needed, though mostly testing through side effects
from flask_babel import gettext as _
from tests.conftest import create_test_user, login_test_user

# Example valid PushSubscription object from a browser
SAMPLE_SUBSCRIPTION_1 = {
    "endpoint": "https://example.com/push/JzQUG2ldy...",
    "expirationTime": None,
    "keys": {
        "p256dh": "BCEzZ0G...",
        "auth": "RAG5J..."
    }
}

SAMPLE_SUBSCRIPTION_2 = {
    "endpoint": "https://example.net/push/ અલગ...", # Different endpoint
    "expirationTime": None,
    "keys": {
        "p256dh": "નોંધણી...",
        "auth": "ቁልፍ..."
    }
}


def test_subscribe_push_notifications(auth_client, user1_fixture):
    response = auth_client.post('/notifications/subscribe', json=SAMPLE_SUBSCRIPTION_1)
    assert response.status_code == 201 # Created
    # My API returns {'message': _('Successfully subscribed to push notifications.')}
    assert 'Successfully subscribed' in response.json['message']

    with auth_client.application.app_context():
        subs = PushSubscription.query.filter_by(user_id=user1_fixture.id).all()
        assert len(subs) == 1
        assert json.loads(subs[0].subscription_json)['endpoint'] == SAMPLE_SUBSCRIPTION_1['endpoint']

def test_subscribe_push_notifications_duplicate(auth_client, user1_fixture):
    auth_client.post('/notifications/subscribe', json=SAMPLE_SUBSCRIPTION_1) # First time
    response = auth_client.post('/notifications/subscribe', json=SAMPLE_SUBSCRIPTION_1) # Duplicate
    assert response.status_code == 200 # OK, already exists (as per my implementation)
    assert 'Subscription already exists' in response.json['message']

    with auth_client.application.app_context():
        subs = PushSubscription.query.filter_by(user_id=user1_fixture.id).all()
        assert len(subs) == 1 # Should still be only one

def test_subscribe_push_notifications_missing_endpoint_in_payload(auth_client):
    invalid_subscription = SAMPLE_SUBSCRIPTION_1.copy()
    del invalid_subscription['endpoint']
    response = auth_client.post('/notifications/subscribe', json=invalid_subscription)
    assert response.status_code == 400 
    assert 'Invalid subscription data. Endpoint is required.' in response.json['error']

def test_subscribe_push_notifications_empty_payload(auth_client):
    response = auth_client.post('/notifications/subscribe', json={})
    assert response.status_code == 400
    assert 'Invalid subscription data. Endpoint is required.' in response.json['error']


def test_unsubscribe_push_notifications(auth_client, user1_fixture):
    # Subscribe first
    auth_client.post('/notifications/subscribe', json=SAMPLE_SUBSCRIPTION_1)
    auth_client.post('/notifications/subscribe', json=SAMPLE_SUBSCRIPTION_2) # Add a second one

    # Unsubscribe SAMPLE_SUBSCRIPTION_1
    response = auth_client.post('/notifications/unsubscribe', json={'endpoint': SAMPLE_SUBSCRIPTION_1['endpoint']})
    assert response.status_code == 200
    assert 'Successfully unsubscribed' in response.json['message']

    with auth_client.application.app_context():
        subs = PushSubscription.query.filter_by(user_id=user1_fixture.id).all()
        assert len(subs) == 1
        assert json.loads(subs[0].subscription_json)['endpoint'] == SAMPLE_SUBSCRIPTION_2['endpoint']

def test_unsubscribe_push_notifications_not_found(auth_client):
    response = auth_client.post('/notifications/unsubscribe', json={'endpoint': 'https://nonexistent.com/push'})
    assert response.status_code == 404
    assert 'Subscription not found' in response.json['error']

def test_unsubscribe_push_notifications_missing_endpoint(auth_client):
    response = auth_client.post('/notifications/unsubscribe', json={}) # Empty payload
    assert response.status_code == 400
    assert 'Subscription endpoint is required' in response.json['error']
    
def test_unsubscribe_others_subscription(auth_client, client, user1_fixture, app):
    # user1_fixture (auth_client) subscribes
    auth_client.post('/notifications/subscribe', json=SAMPLE_SUBSCRIPTION_1)

    # user2 (client) tries to unsubscribe user1's subscription
    user2_username = 'push_user2'
    user2_email = 'pushuser2@example.com'
    # Use helpers from conftest
    reg_response = create_test_user(client, user2_username, user2_email)
    assert reg_response.status_code == 201
    
    login_response = login_test_user(client, user2_email)
    assert login_response.status_code == 200 # client is now user2

    response = client.post('/notifications/unsubscribe', json={'endpoint': SAMPLE_SUBSCRIPTION_1['endpoint']})
    assert response.status_code == 404 # Not found for this user (user2)
    assert 'Subscription not found' in response.json['error']
    
    # Ensure user1's subscription is still there
    with app.app_context():
        subs = PushSubscription.query.filter_by(user_id=user1_fixture.id).all()
        assert len(subs) == 1


# --- Tests for Sending Notifications (Side-effects) ---

@patch('app.services.notification_service.webpush') # Mock the actual webpush call
def test_send_notification_on_badge_earned(mock_webpush, auth_client, user1_fixture, app):
    # 1. Ensure user has a push subscription
    with app.app_context():
        PushSubscription.query.filter_by(user_id=user1_fixture.id).delete() # Clear previous subscriptions for this user for predictability
        db.session.commit()
        sub_info_str = json.dumps(SAMPLE_SUBSCRIPTION_1) # SAMPLE_SUBSCRIPTION_1 from previous tests
        ps = PushSubscription(user_id=user1_fixture.id, subscription_json=sub_info_str)
        db.session.add(ps)
        db.session.commit()
        # db.session.refresh(user1_fixture) # Refresh user to load push_subscriptions relationship - not strictly needed as service re-fetches user

    # 2. Trigger an action that awards a badge (e.g., first comment)
    # Create a block to comment on (using API to ensure block exists for comment)
    block_res = auth_client.post('/blocks/', data={'name': 'NotifyBlockBadge', 'difficulty': 'V0'})
    assert block_res.status_code == 201, f"Block creation failed: {block_res.json}"
    block_id = block_res.json['block']['id']
    
    # Post the comment that should trigger the badge
    # Ensure this is the first comment for this user in this session to guarantee badge award
    with app.app_context():
        Comment.query.filter_by(user_id=user1_fixture.id).delete()
        UserBadge.query.filter_by(user_id=user1_fixture.id).delete() # Clear previous badges too
        db.session.commit()

    comment_res = auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'A comment to earn a badge for notification test'})
    assert comment_res.status_code == 201, f"Posting comment failed: {comment_res.json}"

    # 3. Assert mock_webpush was called
    assert mock_webpush.called, "webpush was not called"
    assert mock_webpush.call_count == 1 # Assuming one subscription, one badge
    
    args, kwargs = mock_webpush.call_args
    assert kwargs['subscription_info']['endpoint'] == SAMPLE_SUBSCRIPTION_1['endpoint']
    payload_sent = json.loads(kwargs['data'])
    assert "New Badge Earned!" in payload_sent['title']
    # The name comes from PREDEFINED_BADGES in badge_service.py
    from app.services.badge_service import PREDEFINED_BADGES 
    assert PREDEFINED_BADGES[BADGE_FIRST_COMMENT]["name"] in payload_sent['body']


@patch('app.services.notification_service.webpush')
def test_send_notification_to_followers_on_new_block(mock_webpush, auth_client, client, user1_fixture, app):
    # user1_fixture is the uploader (auth_client)
    # client will be user2, the follower

    # 1. Create user2 and make them subscribe to notifications
    user2_username = 'follower_for_notif'
    user2_email = 'follower_notif@example.com'
    
    # Ensure user2 is clean for this test
    with app.app_context():
        existing_user2 = User.query.filter_by(email=user2_email).first()
        if existing_user2:
            PushSubscription.query.filter_by(user_id=existing_user2.id).delete()
            # Potentially remove from user1_fixture's followers if already following from other tests
            if user1_fixture.followed.filter_by(id=existing_user2.id).count() > 0:
                 user1_fixture.followed.remove(existing_user2)
            db.session.delete(existing_user2)
            db.session.commit()

    reg_res = create_test_user(client, user2_username, user2_email)
    assert reg_res.status_code == 201, f"Failed to register user2: {reg_res.json}"
    login_res = login_test_user(client, user2_email) # client is now user2
    assert login_res.status_code == 200, f"Failed to login user2: {login_res.json}"
    
    with app.app_context():
        user2 = User.query.filter_by(email=user2_email).first()
        assert user2 is not None, "User2 was not created or found"
        sub_info_str_user2 = json.dumps(SAMPLE_SUBSCRIPTION_2) # Use a different subscription object
        ps_user2 = PushSubscription(user_id=user2.id, subscription_json=sub_info_str_user2)
        db.session.add(ps_user2)
        db.session.commit()
        # db.session.refresh(user2) # Not strictly necessary as we're not checking user2.push_subscriptions directly

    # 2. user2 (client) follows user1 (auth_client's user)
    follow_res = client.post(f'/users/{user1_fixture.id}/follow')
    assert follow_res.status_code == 200, f"User2 failed to follow user1: {follow_res.json}"

    # 3. user1 (auth_client) creates a new block
    block_name_for_notif = "BlockForFollowerNotification"
    create_block_res = auth_client.post('/blocks/', data={'name': block_name_for_notif, 'difficulty': 'V1'})
    assert create_block_res.status_code == 201, f"User1 failed to create block: {create_block_res.json}"

    # 4. Assert mock_webpush was called for user2
    assert mock_webpush.called, "webpush was not called"
    called_for_user2 = False
    for call_args in mock_webpush.call_args_list:
        args, kwargs = call_args
        if kwargs['subscription_info']['endpoint'] == SAMPLE_SUBSCRIPTION_2['endpoint']:
            called_for_user2 = True
            payload_sent = json.loads(kwargs['data'])
            assert "New Block Alert!" in payload_sent['title']
            assert user1_fixture.username in payload_sent['body'] # Uploader's name
            assert block_name_for_notif in payload_sent['body'] # Block name
            break
    assert called_for_user2, "Push notification was not sent to the follower's specific subscription."


@patch('app.services.notification_service.webpush')
def test_notification_expired_subscription_deletion(mock_webpush, auth_client, user1_fixture, app):
    # Simulate WebPushException for an expired subscription
    # The response object needs a status_code attribute
    mock_response = type('MockResponse', (), {'status_code': 410})()
    mock_webpush.side_effect = WebPushException("Gone", response=mock_response)

    with app.app_context():
        PushSubscription.query.filter_by(user_id=user1_fixture.id).delete() # Clear previous for predictability
        db.session.commit()
        sub_info_str = json.dumps(SAMPLE_SUBSCRIPTION_1)
        ps = PushSubscription(user_id=user1_fixture.id, subscription_json=sub_info_str)
        db.session.add(ps)
        db.session.commit()
        assert PushSubscription.query.filter_by(user_id=user1_fixture.id).count() == 1

    # Trigger an action that sends a notification (e.g., award a badge)
    # Using direct service call for simplicity here
    with app.app_context():
        _ensure_badge_exists(BADGE_FIRST_COMMENT) # Ensure badge definition exists
        # award_badge will attempt to send notification
        award_badge(user1_fixture.id, BADGE_FIRST_COMMENT) 

    # Assert that the subscription was deleted
    with app.app_context():
        # db.session.refresh(user1_fixture) # Refresh to see updated relationship, though not strictly needed
        assert PushSubscription.query.filter_by(user_id=user1_fixture.id).count() == 0
