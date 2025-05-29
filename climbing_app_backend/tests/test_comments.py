# tests/test_comments.py
import pytest
from app.models.models import Comment, db, User # Adjusted import
from flask_babel import gettext as _ # For asserting translated messages if needed

# Helper fixture to create a comment directly for testing PUT/DELETE
@pytest.fixture
def create_comment_direct(app, auth_client, create_block):
    # auth_client has 'defaultuser' logged in.
    # We need this user's ID to associate the comment correctly.
    with app.app_context():
        # Assuming 'defaultuser' is the user logged in by auth_client
        # This user is created by client.auth.register in conftest.py
        default_user = User.query.filter_by(username='defaultuser').first()
        if not default_user:
            # Fallback if defaultuser is somehow not created or named differently
            # This indicates an issue with conftest.py's auth_client setup consistency
            pytest.fail("Default user for auth_client not found. Check conftest.py.")
        
        user_id_for_comment = default_user.id
        
    block_json = create_block() # Create a block to comment on
    
    def _make_comment(text='Initial comment text'):
        with app.app_context(): # Ensure DB operations are within app context
            comment = Comment(text=text, block_id=block_json['id'], user_id=user_id_for_comment)
            db.session.add(comment)
            db.session.commit()
            return comment
    return _make_comment

def test_update_own_comment(auth_client, create_comment_direct):
    comment = create_comment_direct(text='Original Comment')
    
    response = auth_client.put(f'/comments/{comment.id}', json={'text': 'Updated Comment Text'})
    assert response.status_code == 200
    assert response.json['comment']['text'] == 'Updated Comment Text'
    # Assuming the message is not translated or test environment uses 'en' as default for messages
    assert response.json['message'] == 'Comment updated successfully'

    # Verify in DB
    updated_comment_db = Comment.query.get(comment.id)
    assert updated_comment_db.text == 'Updated Comment Text'

def test_update_comment_empty_text(auth_client, create_comment_direct):
    comment = create_comment_direct()
    response = auth_client.put(f'/comments/{comment.id}', json={'text': '   '}) # Empty or whitespace
    assert response.status_code == 400
    assert response.json['error'] == 'Comment text cannot be empty' # Match your actual error message

def test_update_other_users_comment(client, auth_client, create_comment_direct, app):
    # Comment created by auth_client's user (defaultuser)
    comment = create_comment_direct()

    # Register and login a second user
    # client.auth is available from conftest.py if client is an instance of the test_client
    # However, the 'client' fixture is a raw, unauthenticated client.
    # We need to use its post method for registration/login.
    
    reg_res = client.post('/auth/register', json={'username': 'user2', 'email': 'user2@example.com', 'password': 'password'})
    assert reg_res.status_code == 201 # Ensure user2 registered
    
    login_res = client.post('/auth/login', json={'email': 'user2@example.com', 'password': 'password'})
    assert login_res.status_code == 200 # client is now authenticated as user2

    response_user2 = client.put(f'/comments/{comment.id}', json={'text': 'User2 trying to edit'})
    assert response_user2.status_code == 403 
    assert response_user2.json['error'] == 'You are not authorized to edit this comment'

def test_delete_own_comment(auth_client, create_comment_direct):
    comment = create_comment_direct()
    comment_id = comment.id
    
    response = auth_client.delete(f'/comments/{comment_id}')
    assert response.status_code == 200 # Or 204 if no body
    assert response.json['message'] == 'Comment deleted successfully'

    # Verify in DB
    deleted_comment_db = Comment.query.get(comment_id)
    assert deleted_comment_db is None

def test_delete_other_users_comment(client, auth_client, create_comment_direct, app):
    comment = create_comment_direct() # Created by auth_client's user (defaultuser)

    # Register and login user2
    reg_res = client.post('/auth/register', json={'username': 'user2del', 'email': 'user2del@example.com', 'password': 'password'})
    assert reg_res.status_code == 201
    
    login_res = client.post('/auth/login', json={'email': 'user2del@example.com', 'password': 'password'})
    assert login_res.status_code == 200 # client is now user2del

    response_user2 = client.delete(f'/comments/{comment.id}')
    assert response_user2.status_code == 403
    assert response_user2.json['error'] == 'You are not authorized to delete this comment'
