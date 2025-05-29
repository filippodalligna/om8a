# tests/test_notifications.py
import pytest
import json
from app.models.models import PushSubscription, User, db # Adjust import
from flask_babel import gettext as _ # For asserting translated messages if needed
from tests.conftest import create_test_user, login_test_user # Import helpers if they are in conftest

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
