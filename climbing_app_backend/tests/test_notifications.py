# tests/test_notifications.py
import pytest
import json
from unittest.mock import patch, call
from flask import current_app # Added
from app.models.models import PushSubscription, User, db, Comment, UserAttempt, ClimbingBlock, Badge, UserBadge # Added Badge, UserBadge
from app.services.badge_service import award_badge, _ensure_badge_exists, BADGE_FIRST_COMMENT, BADGE_BLOCK_UPLOADER, BADGE_FIRST_COMPLETED_CLIMB, PREDEFINED_BADGES # Added PREDEFINED_BADGES
from app.services.notification_service import ( # Added notification type constants
    send_notification,
    NOTIFICATION_TYPE_BADGE_EARNED,
    NOTIFICATION_TYPE_NEW_BLOCK_BY_FOLLOWED,
    NOTIFICATION_TYPE_COMMENT_ON_OWN_BLOCK
)
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


# --- Tests for Notification Preferences ---

def set_user_notification_preference(app, user_id, pref_key, value):
    with app.app_context():
        user = User.query.get(user_id)
        setattr(user, pref_key, value)
        db.session.commit()

@patch('app.services.notification_service.webpush')
def test_notification_preference_badge_earned(mock_webpush, auth_client, user1_fixture, app, create_block):
    # Ensure user has a push subscription
    with app.app_context():
        PushSubscription.query.filter_by(user_id=user1_fixture.id).delete()
        ps = PushSubscription(user_id=user1_fixture.id, subscription_json=json.dumps(SAMPLE_SUBSCRIPTION_1))
        db.session.add(ps)
        db.session.commit()

    # Test Case 1: Preference is True (default) - Should send
    set_user_notification_preference(app, user1_fixture.id, 'notify_on_badge_earned', True)
    # Trigger badge award (e.g., first comment)
    block_json = create_block(name="Badge Pref Block True")
    # Ensure this is the first comment for this user in this session to guarantee badge award
    with app.app_context():
        Comment.query.filter_by(user_id=user1_fixture.id).delete()
        badge_to_check = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_FIRST_COMMENT]["name"]).first()
        if badge_to_check:
            UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_to_check.id).delete()
        db.session.commit()
    auth_client.post(f'/blocks/{block_json["id"]}/comments', json={'text': 'Comment for badge pref test (pref true)'})
    mock_webpush.assert_called()
    mock_webpush.reset_mock()

    # Test Case 2: Preference is False - Should NOT send
    set_user_notification_preference(app, user1_fixture.id, 'notify_on_badge_earned', False)
    # Trigger another action that would award a *different* badge (First Summit)
    with app.app_context():
        badge_summit_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_FIRST_COMPLETED_CLIMB]["name"]).first()
        if badge_summit_def: # Ensure badge definition exists
            UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_summit_def.id).delete()
        # Ensure no completed attempts exist to guarantee badge award
        UserAttempt.query.filter_by(user_id=user1_fixture.id, status='completed').delete()
        db.session.commit()

    block_json_2 = create_block(name="Badge Pref Block False")
    auth_client.post('/history/attempts', json={'block_id': block_json_2['id'], 'status': 'completed'})
    mock_webpush.assert_not_called()


@patch('app.services.notification_service.webpush')
def test_notification_preference_new_block_by_followed(mock_webpush, auth_client, client, user1_fixture, user2_details_fixture, app):
    # user1_fixture is uploader (auth_client)
    # user2_details_fixture is follower (client)

    # Ensure user2 has a push subscription
    with app.app_context():
        PushSubscription.query.filter_by(user_id=user2_details_fixture['id']).delete()
        ps_user2 = PushSubscription(user_id=user2_details_fixture['id'], subscription_json=json.dumps(SAMPLE_SUBSCRIPTION_2))
        db.session.add(ps_user2)
        # Ensure user2 is following user1
        user1 = User.query.get(user1_fixture.id)
        user2 = User.query.get(user2_details_fixture['id'])
        if not user1.followers.filter(User.id == user2.id).count() > 0: # Check if user2 is a follower of user1
             user2.followed.append(user1) # If not, user2 follows user1
        db.session.commit()

    login_test_user(client, user2_details_fixture['email']) # client is now user2

    # Test Case 1: Follower's preference is True - Should send
    set_user_notification_preference(app, user2_details_fixture['id'], 'notify_on_new_block_by_followed', True)
    create_block_response = auth_client.post('/blocks/', data={'name': 'Notify Follower Block True', 'difficulty': 'V1'}) # user1 creates block
    assert create_block_response.status_code == 201
    created_block_id = create_block_response.json['block']['id']

    mock_webpush.assert_called_with(
        subscription_info=SAMPLE_SUBSCRIPTION_2,
        data=json.dumps({
            "title": "New Block Alert!",
            "body": f"{user1_fixture.username} just added a new block: Notify Follower Block True",
            "url": f"/blocks/{created_block_id}"
        }),
        vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
        vapid_claims=current_app.config['VAPID_CLAIMS']
    )
    mock_webpush.reset_mock()

    # Test Case 2: Follower's preference is False - Should NOT send
    set_user_notification_preference(app, user2_details_fixture['id'], 'notify_on_new_block_by_followed', False)
    auth_client.post('/blocks/', data={'name': 'Notify Follower Block False', 'difficulty': 'V2'}) # user1 creates another block
    mock_webpush.assert_not_called()


@patch('app.services.notification_service.webpush')
def test_notification_preference_comment_on_own_block(mock_webpush, auth_client, client, user1_fixture, user2_details_fixture, create_block, app):
    # user1_fixture is block owner (auth_client)
    # user2_details_fixture is commenter (client)
    block_json = create_block(name="Comment Pref Block") # Block created by user1 (auth_client)

    # Ensure user1 (block owner) has a push subscription
    with app.app_context():
        PushSubscription.query.filter_by(user_id=user1_fixture.id).delete()
        ps_user1 = PushSubscription(user_id=user1_fixture.id, subscription_json=json.dumps(SAMPLE_SUBSCRIPTION_1))
        db.session.add(ps_user1)
        db.session.commit()

    login_test_user(client, user2_details_fixture['email']) # client is now user2

    # Test Case 1: Block owner's preference is True - Should send
    set_user_notification_preference(app, user1_fixture.id, 'notify_on_comment_on_own_block', True)
    comment_text = "A comment from user2 on user1's block (pref true)"
    client.post(f'/blocks/{block_json["id"]}/comments', json={'text': comment_text})

    expected_payload = {
        "title": "New Comment on Your Block",
        "body": f"{user2_details_fixture['username']} commented on your block '{block_json['name']}': {comment_text[:50] + '...' if len(comment_text) > 50 else comment_text}",
        "url": f"/blocks/{block_json['id']}/comments"
    }
    mock_webpush.assert_called_with(
        subscription_info=SAMPLE_SUBSCRIPTION_1,
        data=json.dumps(expected_payload),
        vapid_private_key=current_app.config['VAPID_PRIVATE_KEY'],
        vapid_claims=current_app.config['VAPID_CLAIMS']
    )
    mock_webpush.reset_mock()

    # Test Case 2: Block owner's preference is False - Should NOT send
    set_user_notification_preference(app, user1_fixture.id, 'notify_on_comment_on_own_block', False)
    client.post(f'/blocks/{block_json["id"]}/comments', json={'text': "Another comment from user2 (pref false)"})
    mock_webpush.assert_not_called()

@patch('app.services.notification_service.webpush')
def test_comment_on_own_block_no_notification_to_self(mock_webpush, auth_client, user1_fixture, create_block, app):
    # user1_fixture (auth_client) comments on their own block
    block_json = create_block(name="Self Comment Block") # Block created by user1

    # Ensure user1 (block owner) has a push subscription and pref is True
    with app.app_context():
        PushSubscription.query.filter_by(user_id=user1_fixture.id).delete()
        ps_user1 = PushSubscription(user_id=user1_fixture.id, subscription_json=json.dumps(SAMPLE_SUBSCRIPTION_1))
        db.session.add(ps_user1)
        db.session.commit()
    set_user_notification_preference(app, user1_fixture.id, 'notify_on_comment_on_own_block', True)

    # user1 posts a comment on their own block
    auth_client.post(f'/blocks/{block_json["id"]}/comments', json={'text': "User1 commenting own block"})
    mock_webpush.assert_not_called() # Should not notify self for own comment
