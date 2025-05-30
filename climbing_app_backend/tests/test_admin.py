# tests/test_admin.py
import pytest
from app.models.models import User, ClimbingBlock, db
from tests.conftest import create_test_user, login_test_user # Helpers from conftest

# Fixture to create an admin user directly in DB for testing
@pytest.fixture
def admin_user(app): # Depends on the app fixture from conftest.py
    with app.app_context():
        admin = User.query.filter_by(email='admin@example.com').first()
        if not admin: # Create only if it doesn't exist to avoid issues with multiple calls
            admin = User(username='admin_user', email='admin@example.com', is_admin=True)
            admin.set_password('adminpass') # Assuming set_password method on User model
            db.session.add(admin)
            db.session.commit()
        elif not admin.is_admin: # If user exists but is not admin, make them admin
            admin.is_admin = True
            db.session.commit()
        return admin

@pytest.fixture
def admin_client(client, admin_user): # Depends on client and admin_user fixtures
    # Log in the admin user
    login_res = login_test_user(client, 'admin@example.com', 'adminpass')
    assert login_res.status_code == 200, f"Admin login failed: {login_res.json}"
    return client


def test_get_all_blocks_as_admin(admin_client, create_block_db, user1_fixture): # user1_fixture from conftest
    # user1_fixture will be used as a default uploader if its ID is 1
    # If create_block_db defaults to uploader_id=1, and user1_fixture.id is 1, it works.
    # Otherwise, explicitly pass user1_fixture.id.
    create_block_db(name="Admin Block 1", difficulty="V1", uploader_id=user1_fixture.id)
    create_block_db(name="Admin Block 2", difficulty="V2", uploader_id=user1_fixture.id)

    response = admin_client.get('/admin/blocks/all?per_page=5')
    assert response.status_code == 200
    # Based on my app, total_blocks is the key for total count
    assert response.json['total_blocks'] >= 2
    assert len(response.json['blocks']) >= 2
    assert 'uploader_username' in response.json['blocks'][0]
    assert 'updated_at' in response.json['blocks'][0]


def test_get_all_blocks_as_non_admin(auth_client): # auth_client is a regular logged-in user
    response = auth_client.get('/admin/blocks/all')
    assert response.status_code == 403
    assert 'Admin access required' in response.json['error']


def test_get_all_blocks_unauthenticated(client):
    response = client.get('/admin/blocks/all')
    assert response.status_code == 403
    assert 'Admin access required' in response.json['error']


def test_get_blocks_needing_photo_as_admin(admin_client, create_block_db, app, user1_fixture):
    # Clean up blocks to ensure count is predictable for this test
    with app.app_context():
        ClimbingBlock.query.delete()
        db.session.commit()

    b1 = create_block_db(name="Block With Photo Needs", difficulty="V0", uploader_id=user1_fixture.id)
    b2 = create_block_db(name="Block No Photo Needs", difficulty="V0", uploader_id=user1_fixture.id) # This one should be found
    b3 = create_block_db(name="Block Also With Photo Needs", difficulty="V1", uploader_id=user1_fixture.id)

    with app.app_context():
        b1_db = ClimbingBlock.query.get(b1.id)
        b1_db.photo_filename = "some_photo.jpg"
        # b2_db (Block No Photo Needs) already has photo_filename as None
        b3_db = ClimbingBlock.query.get(b3.id)
        b3_db.photo_filename = "another_photo.jpg"
        db.session.commit()

    response = admin_client.get('/admin/blocks/needs-photo?per_page=5')
    assert response.status_code == 200
    assert response.json['total_blocks'] == 1 # Only b2 should be listed
    assert len(response.json['blocks']) == 1
    assert response.json['blocks'][0]['name'] == "Block No Photo Needs"
    assert response.json['blocks'][0]['photo_filename'] is None


def test_get_blocks_needing_photo_as_non_admin(auth_client):
    response = auth_client.get('/admin/blocks/needs-photo')
    assert response.status_code == 403


# --- Tests for Admin Update/Delete Block ---

def test_update_block_by_admin(admin_client, create_block_db, app):
    # 1. Create a block to update
    # uploader_id=1 is assumed to exist from admin_user or user1_fixture (defaultuser)
    block = create_block_db(name="Original Name", difficulty="V5", highlight_data="Old data", uploader_id=1)
    block_id = block.id

    update_data = {
        "name": "Updated Block Name by Admin",
        "difficulty": "V6",
        "highlight_data": "New highlight data"
    }
    response = admin_client.put(f'/admin/blocks/{block_id}', json=update_data)
    assert response.status_code == 200
    assert 'Block updated successfully' in response.json['message']
    updated_block_json = response.json['block']
    assert updated_block_json['name'] == update_data['name']
    assert updated_block_json['difficulty'] == update_data['difficulty']
    assert updated_block_json['highlight_data'] == update_data['highlight_data']
    assert updated_block_json['id'] == block_id

    assert 'updated_at' in updated_block_json
    # To robustly check updated_at, we'd compare, but ensuring it's there is a good start.
    # with app.app_context():
    #     updated_block_db = ClimbingBlock.query.get(block_id)
    #     assert updated_block_db.updated_at > block.created_at # Simplistic check


def test_update_block_by_admin_partial(admin_client, create_block_db):
    block = create_block_db(name="Partial Update", difficulty="V3", uploader_id=1)
    block_id = block.id
    original_difficulty = block.difficulty

    update_data = {"name": "Partial Name Update by Admin"}
    response = admin_client.put(f'/admin/blocks/{block_id}', json=update_data)
    assert response.status_code == 200
    assert response.json['block']['name'] == update_data['name']
    assert response.json['block']['difficulty'] == original_difficulty # Difficulty should be unchanged

def test_update_block_by_admin_no_valid_data(admin_client, create_block_db):
    block = create_block_db(name="No Valid Data Block", difficulty="V1", uploader_id=1)
    response = admin_client.put(f'/admin/blocks/{block.id}', json={"unknown_field": "some_value"})
    assert response.status_code == 400
    assert 'No valid fields provided for update' in response.json['message']


def test_update_block_by_admin_empty_name_string(admin_client, create_block_db):
    block = create_block_db(name="Test Empty Name", difficulty="V1", uploader_id=1)
    response = admin_client.put(f'/admin/blocks/{block.id}', json={"name": "  "})
    assert response.status_code == 400
    assert 'Block name cannot be empty' in response.json['error']


def test_update_block_non_admin(auth_client, create_block_db): # auth_client is non-admin
    block = create_block_db(name="NonAdminUpdateAttempt", difficulty="V2", uploader_id=1)
    response = auth_client.put(f'/admin/blocks/{block.id}', json={"name": "Attempted Update"})
    assert response.status_code == 403

def test_update_block_unauthenticated(client, create_block_db):
    block = create_block_db(name="UnauthUpdateAttempt", difficulty="V2", uploader_id=1)
    response = client.put(f'/admin/blocks/{block.id}', json={"name": "Attempted Update"})
    assert response.status_code == 403

def test_delete_block_by_admin(admin_client, create_block_db, app):
    block = create_block_db(name="ToDeleteByAdmin", difficulty="V4", uploader_id=1)
    block_id = block.id

    response = admin_client.delete(f'/admin/blocks/{block_id}')
    assert response.status_code == 200
    assert 'Block deleted successfully' in response.json['message']

    with app.app_context():
        deleted_block = ClimbingBlock.query.get(block_id)
        assert deleted_block is None

def test_delete_block_non_admin(auth_client, create_block_db):
    block = create_block_db(name="NonAdminDeleteAttempt", difficulty="V2", uploader_id=1)
    response = auth_client.delete(f'/admin/blocks/{block.id}')
    assert response.status_code == 403

def test_delete_block_unauthenticated(client, create_block_db):
    block = create_block_db(name="UnauthDeleteAttempt", difficulty="V2", uploader_id=1)
    response = client.delete(f'/admin/blocks/{block.id}')
    assert response.status_code == 403

def test_delete_non_existent_block_by_admin(admin_client):
    response = admin_client.delete('/admin/blocks/999999') # Non-existent ID
    assert response.status_code == 404

# --- Tests for Admin User Listing & Detail View ---

def test_list_users_as_admin(admin_client, app): # admin_client logs in admin_user
    # The admin_user itself will be in the list.
    # Create a couple more users to ensure the list has multiple entries.
    # Using a separate client for registration to avoid session conflicts with admin_client
    temp_client = app.test_client() # Create a fresh client for new registrations
    create_test_user(temp_client, 'user_list_1', 'user_list_1@example.com')
    create_test_user(temp_client, 'user_list_2', 'user_list_2@example.com')

    response = admin_client.get('/admin/users?per_page=5')
    assert response.status_code == 200

    # Check for total users. This depends on how many users are created across all tests.
    # A robust check would be on the presence of known usernames.
    # My conftest.py also creates 'defaultuser'.
    # admin_user fixture creates 'admin_user'.
    # This test creates 'user_list_1', 'user_list_2'.
    # So, at least 4 users.
    assert response.json['total_users'] >= 4
    assert len(response.json['users']) >= 3 # Depending on per_page and total users

    usernames_in_response = [u['username'] for u in response.json['users']]
    assert 'admin_user' in usernames_in_response
    assert 'user_list_1' in usernames_in_response
    assert 'user_list_2' in usernames_in_response

    # Check for expected fields in user data
    first_user_in_list = response.json['users'][0]
    assert 'id' in first_user_in_list
    assert 'username' in first_user_in_list
    assert 'email' in first_user_in_list
    assert 'is_admin' in first_user_in_list
    assert 'created_at' in first_user_in_list


def test_list_users_as_non_admin(auth_client): # auth_client is a regular logged-in user
    response = auth_client.get('/admin/users')
    assert response.status_code == 403
    assert 'Admin access required' in response.json['error']


def test_list_users_unauthenticated(client):
    response = client.get('/admin/users')
    assert response.status_code == 403


def test_get_specific_user_as_admin(admin_client, app):
    target_user_id = None
    with app.app_context():
        # The admin_user fixture ensures 'admin@example.com' exists and is admin.
        admin = User.query.filter_by(email='admin@example.com').first()
        assert admin is not None, "Admin user not found in DB for test setup"
        target_user_id = admin.id

    response = admin_client.get(f'/admin/users/{target_user_id}')
    assert response.status_code == 200
    user_data = response.json
    assert user_data['id'] == target_user_id
    assert user_data['username'] == 'admin_user'
    assert user_data['email'] == 'admin@example.com'
    assert user_data['is_admin'] is True
    assert 'created_at' in user_data


def test_get_specific_user_as_non_admin(auth_client, app, user1_fixture):
    # Get ID of the non-admin user logged in by auth_client
    target_user_id = user1_fixture.id # user1_fixture is 'defaultuser'

    response = auth_client.get(f'/admin/users/{target_user_id}')
    assert response.status_code == 403


def test_get_non_existent_user_as_admin(admin_client):
    response = admin_client.get('/admin/users/999999') # Non-existent ID
    assert response.status_code == 404
