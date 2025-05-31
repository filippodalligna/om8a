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

# --- Tests for Admin User Management (Set Admin Status & Soft Delete) ---

def test_admin_set_user_admin_status(admin_client, app):
    # Create a regular user to be promoted
    target_username = 'user_to_be_admin'
    target_email = 'promoteme@example.com'
    temp_client = app.test_client()
    create_test_user(temp_client, target_username, target_email) # create_test_user is from conftest

    target_user_id = None
    with app.app_context():
        target_user = User.query.filter_by(email=target_email).first()
        assert target_user is not None
        assert not target_user.is_admin # Starts as non-admin
        target_user_id = target_user.id

    # Admin promotes target_user
    response = admin_client.put(f'/admin/users/{target_user_id}/status', json={'is_admin': True})
    assert response.status_code == 200
    assert response.json['user']['is_admin'] is True
    with app.app_context():
        target_user = User.query.get(target_user_id) # Re-fetch or refresh
        assert target_user.is_admin is True

    # Admin demotes target_user
    response = admin_client.put(f'/admin/users/{target_user_id}/status', json={'is_admin': False})
    assert response.status_code == 200
    assert response.json['user']['is_admin'] is False
    with app.app_context():
        target_user = User.query.get(target_user_id) # Re-fetch or refresh
        assert target_user.is_admin is False


def test_admin_set_user_active_status(admin_client, app):
    target_username = 'user_to_be_deactivated'
    target_email = 'deactivateme@example.com'
    temp_client = app.test_client()
    create_test_user(temp_client, target_username, target_email)

    target_user_id = None
    with app.app_context():
        target_user = User.query.filter_by(email=target_email).first()
        assert target_user is not None
        assert target_user.is_active is True # Starts as active (model default)
        target_user_id = target_user.id

    # Admin deactivates target_user
    response = admin_client.put(f'/admin/users/{target_user_id}/status', json={'is_active': False})
    assert response.status_code == 200
    assert response.json['user']['is_active'] is False
    with app.app_context():
        target_user = User.query.get(target_user_id)
        assert target_user.is_active is False

    # Admin reactivates target_user
    response = admin_client.put(f'/admin/users/{target_user_id}/status', json={'is_active': True})
    assert response.status_code == 200
    assert response.json['user']['is_active'] is True
    with app.app_context():
        target_user = User.query.get(target_user_id)
        assert target_user.is_active is True


def test_admin_cannot_demote_self(admin_client, admin_user): # admin_user is the User object for admin_client
    response = admin_client.put(f'/admin/users/{admin_user.id}/status', json={'is_admin': False})
    assert response.status_code == 400
    assert 'Admins cannot remove their own admin status' in response.json['error']


def test_admin_cannot_deactivate_self(admin_client, admin_user):
    response = admin_client.put(f'/admin/users/{admin_user.id}/status', json={'is_active': False})
    assert response.status_code == 400
    assert 'Admins cannot deactivate their own account' in response.json['error']


def test_deactivated_user_cannot_login(client, app, admin_client):
    target_username = 'deactivated_login_test'
    target_email = 'deactivatedlogin@example.com'
    target_password = 'password'

    create_test_user(client, target_username, target_email, target_password)
    target_user_id = None
    with app.app_context():
        target_user = User.query.filter_by(email=target_email).first()
        assert target_user is not None
        target_user_id = target_user.id

    # Admin deactivates the user
    deactivate_response = admin_client.put(f'/admin/users/{target_user_id}/status', json={'is_active': False})
    assert deactivate_response.status_code == 200 # Ensure deactivation was successful

    # Attempt login with deactivated user (using a fresh client for login attempt)
    login_client = app.test_client()
    login_response = login_test_user(login_client, target_email, target_password)
    assert login_response.status_code == 401
    assert 'Invalid credentials' in login_response.json['message'] # Default Flask-Login message if user is inactive


def test_update_user_status_non_admin(auth_client, app):
    # Create a user whose status non-admin will try to change
    target_username = 'target_for_non_admin_put'
    target_email = 'targetput@example.com'
    temp_client = app.test_client()
    create_test_user(temp_client, target_username, target_email)

    target_user_id = None
    with app.app_context():
        target_user = User.query.filter_by(email=target_email).first()
        assert target_user is not None
        target_user_id = target_user.id

    response = auth_client.put(f'/admin/users/{target_user_id}/status', json={'is_admin': True})
    assert response.status_code == 403


def test_update_user_status_invalid_payload(admin_client, admin_user):
    response = admin_client.put(f'/admin/users/{admin_user.id}/status', json={'is_admin': 'not_a_boolean'})
    assert response.status_code == 400
    assert 'No valid fields provided for update' in response.json['message']

    response_empty = admin_client.put(f'/admin/users/{admin_user.id}/status', json={})
    assert response_empty.status_code == 400
    # My implementation returns "Request body cannot be empty."
    assert 'Request body cannot be empty' in response_empty.json['error']

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

# --- Tests for Admin Block Status Management ---
from app.models.models import ALLOWED_BLOCK_STATUSES, BlockProposal, ALLOWED_PROPOSAL_STATUSES # Added BlockProposal and ALLOWED_PROPOSAL_STATUSES
from datetime import datetime # Added for proposal review tests

@pytest.fixture
def create_proposal(auth_client, user1_fixture): # Uses auth_client (non-admin) to propose
    def _make_proposal(location="Test Proposal Location from Fixture", uploader_id_override=None):
        # user1_fixture is the default proposer via auth_client
        proposer_to_use = user1_fixture
        if uploader_id_override: # This part is tricky as auth_client is fixed.
                                 # For simplicity, this fixture will always use user1_fixture (defaultuser) as proposer.
                                 # If tests need different proposers, they should use a different client or direct DB creation.
            pass # Ignoring uploader_id_override for API-based creation via fixed auth_client

        data = {'location_description': location, 'proposed_grade': 'Vfixture'}
        response = auth_client.post('/proposals/', data=data) # auth_client is logged in as user1_fixture
        assert response.status_code == 201, f"Failed to create proposal: {response.json}"
        return response.json['proposal'] # Return created proposal JSON
    return _make_proposal


def test_admin_update_block_status(admin_client, create_block_db, app):
    block = create_block_db(name="Status Test Block", difficulty="V1", uploader_id=1) # Default status 'active'
    block_id = block.id

    new_status = 'hidden_by_admin'
    assert new_status in ALLOWED_BLOCK_STATUSES

    response = admin_client.put(f'/admin/blocks/{block_id}/status', json={'status': new_status})
    assert response.status_code == 200
    assert response.json['message'] == 'Block status updated successfully.'
    assert response.json['block']['status'] == new_status
    assert response.json['block']['id'] == block_id # Ensure the correct block is returned

    with app.app_context():
        updated_block = ClimbingBlock.query.get(block_id)
        assert updated_block.status == new_status

def test_admin_update_block_status_invalid_value(admin_client, create_block_db):
    block = create_block_db(name="Invalid Status Block", difficulty="V1")
    response = admin_client.put(f'/admin/blocks/{block.id}/status', json={'status': 'non_existent_status'})
    assert response.status_code == 400
    assert 'Invalid status value' in response.json['error']

def test_admin_update_block_status_empty_status(admin_client, create_block_db):
    block = create_block_db(name="Empty Status Block", difficulty="V1")
    # The route code checks for `not new_status or new_status.strip() == ""`
    # and `Status field cannot be empty.` for `new_status.strip() == ""`
    # and `Status field is required in the request body.` for `not data or 'status' not in data`

    # Test empty string
    response_empty_str = admin_client.put(f'/admin/blocks/{block.id}/status', json={'status': ''})
    assert response_empty_str.status_code == 400
    assert 'Status field cannot be empty' in response_empty_str.json['error'] # Adjusted to match my route code's message

    # Test status with only spaces
    response_spaces_str = admin_client.put(f'/admin/blocks/{block.id}/status', json={'status': '   '})
    assert response_spaces_str.status_code == 400
    assert 'Status field cannot be empty' in response_spaces_str.json['error'] # Adjusted


def test_admin_update_block_status_missing_status_field(admin_client, create_block_db):
    block = create_block_db(name="Missing Status Field Block", difficulty="V1")
    response = admin_client.put(f'/admin/blocks/{block.id}/status', json={'other_field': 'data'})
    assert response.status_code == 400
    assert 'Status field is required' in response.json['error'] # Adjusted to match my route code's message for missing 'status'

def test_admin_update_block_status_non_admin(auth_client, create_block_db):
    block = create_block_db(name="NonAdminStatusUpdateBlock", difficulty="V1")
    response = auth_client.put(f'/admin/blocks/{block.id}/status', json={'status': 'hidden_by_admin'})
    assert response.status_code == 403 # Non-admin should be forbidden

def test_admin_list_all_blocks_shows_status(admin_client, create_block_db, app):
    # Create blocks with different statuses
    create_block_db(name="Active Block For Status List", difficulty="V0", uploader_id=1, status='active')
    hidden_block = create_block_db(name="Hidden Block For Status List", difficulty="V0", uploader_id=1) # default active

    # Update status of one block to hidden_by_admin using the new endpoint
    update_response = admin_client.put(f'/admin/blocks/{hidden_block.id}/status', json={'status': 'hidden_by_admin'})
    assert update_response.status_code == 200 # Ensure status update was successful

    response = admin_client.get('/admin/blocks/all?per_page=10')
    assert response.status_code == 200

    block_info = {b['name']: {'status': b['status'], 'id': b['id']} for b in response.json['blocks']}

    # Check Active Block
    assert "Active Block For Status List" in block_info
    assert block_info["Active Block For Status List"]['status'] == 'active'

    # Check Hidden Block
    assert "Hidden Block For Status List" in block_info
    assert block_info["Hidden Block For Status List"]['status'] == 'hidden_by_admin'
    assert block_info["Hidden Block For Status List"]['id'] == hidden_block.id

# --- Tests for Admin Block Proposal Management ---

def test_admin_list_pending_proposals(admin_client, create_proposal, app, user1_fixture):
    # Clean up proposals to ensure predictable test
    with app.app_context():
        BlockProposal.query.delete()
        db.session.commit()

    proposal1_data = create_proposal(location="Pending Prop Alpha")
    proposal2_data = create_proposal(location="Pending Prop Beta")

    # Manually set one to a different status to ensure only pending are listed
    with app.app_context():
        prop2_db = BlockProposal.query.get(proposal2_data['id'])
        prop2_db.status = 'approved' # Change status directly for test setup
        db.session.add(prop2_db)
        db.session.commit()

    # Re-create proposal2 as pending for this specific test's expectation of it being pending.
    # The previous change was to test filtering. Let's ensure we have two pending for the listing.
    # For clarity, we'll create a third one that remains pending.
    proposal1_data_pending = create_proposal(location="Actual Pending Prop 1")
    proposal3_data_pending = create_proposal(location="Actual Pending Prop 2")


    response = admin_client.get('/admin/proposals/pending?per_page=5')
    assert response.status_code == 200
    json_data = response.json

    # We expect 2 proposals that were just created as pending.
    # The one manually set to 'approved' (prop2_db) should not be listed.
    assert json_data['total_proposals'] == 2

    proposal_ids_in_response = [p['id'] for p in json_data['proposals']]
    assert proposal1_data_pending['id'] in proposal_ids_in_response
    assert proposal3_data_pending['id'] in proposal_ids_in_response
    assert proposal2_data['id'] not in proposal_ids_in_response # This was approved

    for p_json in json_data['proposals']:
        assert p_json['status'] == 'pending'
        assert 'proposer_username' in p_json
        assert p_json['proposer_id'] == user1_fixture.id # create_proposal uses auth_client (user1_fixture)


def test_admin_review_proposal_approve(admin_client, create_proposal, admin_user, app):
    proposal_data = create_proposal(location="Proposal to Approve")
    proposal_id = proposal_data['id']

    review_data = {'status': 'approved', 'admin_notes': 'Looks good! Ready for next step.'}
    response = admin_client.put(f'/admin/proposals/{proposal_id}/review', json=review_data)
    assert response.status_code == 200
    updated_proposal_json = response.json['proposal']
    assert updated_proposal_json['status'] == 'approved'
    assert updated_proposal_json['admin_notes'] == review_data['admin_notes']
    assert updated_proposal_json['admin_reviewer_id'] == admin_user.id # admin_user is fixture for logged-in admin
    assert 'reviewed_at' in updated_proposal_json and updated_proposal_json['reviewed_at'] is not None

    with app.app_context(): # Verify in DB
        db_proposal = BlockProposal.query.get(proposal_id)
        assert db_proposal is not None
        assert db_proposal.status == 'approved'
        assert db_proposal.admin_reviewer_id == admin_user.id
        assert db_proposal.reviewed_at is not None

def test_admin_review_proposal_reject(admin_client, create_proposal, admin_user, app):
    proposal_data = create_proposal(location="Proposal to Reject")
    proposal_id = proposal_data['id']

    review_data = {'status': 'rejected', 'admin_notes': 'Not suitable for our area.'}
    response = admin_client.put(f'/admin/proposals/{proposal_id}/review', json=review_data)
    assert response.status_code == 200
    updated_proposal_json = response.json['proposal']
    assert updated_proposal_json['status'] == 'rejected'
    assert updated_proposal_json['admin_notes'] == review_data['admin_notes']
    assert updated_proposal_json['admin_reviewer_id'] == admin_user.id

    with app.app_context(): # Verify in DB
        db_proposal = BlockProposal.query.get(proposal_id)
        assert db_proposal is not None
        assert db_proposal.status == 'rejected'

def test_admin_review_proposal_invalid_status_value(admin_client, create_proposal):
    proposal_data = create_proposal(location="Invalid Status Update Prop")
    proposal_id = proposal_data['id']
    response = admin_client.put(f'/admin/proposals/{proposal_id}/review', json={'status': 'on_hold_pending_review_again'})
    assert response.status_code == 400
    assert 'Invalid status value' in response.json['error']

def test_admin_review_proposal_missing_status_field(admin_client, create_proposal):
    proposal_data = create_proposal(location="Missing Status Field Prop Review")
    proposal_id = proposal_data['id']
    response = admin_client.put(f'/admin/proposals/{proposal_id}/review', json={'admin_notes': 'Some notes but no status provided.'})
    assert response.status_code == 400
    assert 'Status field is required' in response.json['error'] # Based on my admin route for review

def test_admin_review_non_existent_proposal(admin_client):
    response = admin_client.put('/admin/proposals/999999/review', json={'status': 'approved'})
    assert response.status_code == 404 # Not Found
