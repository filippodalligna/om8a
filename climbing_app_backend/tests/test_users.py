# tests/test_users.py
import pytest
from app.models.models import User, db # Adjust import

def create_test_user(client, username, email, password='password'):
    # Helper to register a new user via API for testing.
    return client.post('/auth/register', json={
        'username': username, 'email': email, 'password': password
    })

def login_test_user(client, email, password='password'):
    # Helper to log in a user via API for testing.
    return client.post('/auth/login', json={'email': email, 'password': password})

@pytest.fixture(scope='function')
def user1_fixture(auth_client):
    # auth_client is already logged in as a user (typically user_id=1)
    # Return the User object for this user
    with auth_client.application.app_context():
        user = User.query.filter_by(email='default@example.com').first() # Default email from my auth_client
        if not user:
            # Fallback if the default user from auth_client isn't found by that email
            # This might happen if auth_client's details change or it's the very first user (ID 1)
            user = User.query.get(1) 
        if not user:
            pytest.skip("Default user for auth_client not reliably found, skipping dependent tests.")
        return user


@pytest.fixture(scope='function')
def user2_details_fixture(client, app): # Added app fixture for db access
    username = 'user2_social'
    email = 'user2social@example.com'
    create_test_user(client, username, email) # Use the unauthenticated client to register
    with app.app_context(): # Use app.app_context() for database operations
        user = User.query.filter_by(email=email).first()
        if not user:
            pytest.skip("Failed to create user2_social for tests.")
        return {'id': user.id, 'username': username, 'email': email}

def test_follow_user(auth_client, user1_fixture, user2_details_fixture):
    # user1 (auth_client) follows user2
    response = auth_client.post(f'/users/{user2_details_fixture["id"]}/follow')
    assert response.status_code == 200
    assert f"You are now following {user2_details_fixture['username']}" in response.json['message']

    with auth_client.application.app_context():
        db.session.refresh(user1_fixture) 
        assert user1_fixture.followed.filter(User.id == user2_details_fixture["id"]).count() == 1


def test_follow_self(auth_client, user1_fixture):
    response = auth_client.post(f'/users/{user1_fixture.id}/follow')
    assert response.status_code == 400
    assert 'You cannot follow yourself' in response.json['error']


def test_follow_already_following(auth_client, user1_fixture, user2_details_fixture):
    auth_client.post(f'/users/{user2_details_fixture["id"]}/follow') # First follow
    response = auth_client.post(f'/users/{user2_details_fixture["id"]}/follow') # Attempt second follow
    assert response.status_code == 400
    assert 'You are already following this user' in response.json['message']


def test_unfollow_user(auth_client, user1_fixture, user2_details_fixture):
    auth_client.post(f'/users/{user2_details_fixture["id"]}/follow') # Follow first
    response = auth_client.delete(f'/users/{user2_details_fixture["id"]}/follow') # Then unfollow
    assert response.status_code == 200
    assert f"You have unfollowed {user2_details_fixture['username']}" in response.json['message']

    with auth_client.application.app_context():
        db.session.refresh(user1_fixture)
        assert user1_fixture.followed.filter(User.id == user2_details_fixture["id"]).count() == 0


def test_unfollow_not_following(auth_client, user1_fixture, user2_details_fixture):
    response = auth_client.delete(f'/users/{user2_details_fixture["id"]}/follow')
    assert response.status_code == 400
    assert 'You are not following this user' in response.json['message']


def test_list_followers(auth_client, client, user1_fixture, user2_details_fixture, app):
    # user2 (represented by 'client' after login) follows user1_fixture
    with app.app_context(): # Ensure client operations are within context if they touch db indirectly
        login_test_user(client, user2_details_fixture['email']) 

    client.post(f'/users/{user1_fixture.id}/follow')

    response = auth_client.get(f'/users/{user1_fixture.id}/followers')
    assert response.status_code == 200
    assert response.json['total'] >= 1 # Check for at least 1
    follower_usernames = [f['username'] for f in response.json['followers']]
    assert user2_details_fixture['username'] in follower_usernames


def test_list_following(auth_client, user1_fixture, user2_details_fixture):
    # user1_fixture (auth_client) follows user2_details_fixture
    auth_client.post(f'/users/{user2_details_fixture["id"]}/follow')

    response = auth_client.get(f'/users/{user1_fixture.id}/following')
    assert response.status_code == 200
    assert response.json['total'] >= 1 
    following_usernames = [f['username'] for f in response.json['following']]
    assert user2_details_fixture['username'] in following_usernames

def test_list_followers_pagination(auth_client, client, user1_fixture, app):
    with app.app_context():
        # Ensure users are created and logged in with separate clients to avoid session conflicts
        follower_users = []
        for i in range(3):
            username = f'follower_p{i}'
            email = f'follower_p{i}@example.com'
            
            # Create a new client for each user's operations
            temp_page_client = app.test_client()
            
            reg_response = create_test_user(temp_page_client, username, email)
            assert reg_response.status_code == 201 # Ensure user registration
            
            login_response = login_test_user(temp_page_client, email)
            assert login_response.status_code == 200 # Ensure user login
            
            # This user (temp_page_client) follows user1_fixture
            follow_response = temp_page_client.post(f'/users/{user1_fixture.id}/follow')
            assert follow_response.status_code == 200 # Ensure follow action

            follower_user = User.query.filter_by(email=email).first()
            assert follower_user is not None
            follower_users.append(follower_user)
    
    # Now check pagination for user1_fixture's followers
    # Use the main 'client' or 'auth_client' which is not following/followed by these new users
    response = client.get(f'/users/{user1_fixture.id}/followers?page=1&per_page=2')
    assert response.status_code == 200
    assert len(response.json['followers']) == 2
    assert response.json['total'] == 3 # Total followers created for user1_fixture
    assert response.json['pages'] == 2
    assert response.json['current_page'] == 1

    response_p2 = client.get(f'/users/{user1_fixture.id}/followers?page=2&per_page=2')
    assert response_p2.status_code == 200
    assert len(response_p2.json['followers']) == 1 # Remaining follower on page 2
