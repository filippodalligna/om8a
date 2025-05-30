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
