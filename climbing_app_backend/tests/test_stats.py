# tests/test_stats.py
import pytest
from app.models.models import User, ClimbingBlock, UserAttempt, db
from app.services.stats_service import get_user_stats # For direct service testing (optional)
from app.utils.difficulty import V_SCALE_MAPPING
from datetime import datetime, timedelta # Added timedelta for completeness, though not used in these specific tests
from tests.conftest import create_test_user # Helper from conftest

# Assuming user1_fixture and admin_client are from conftest.py
# Assuming create_block_db and log_completed_climb_for_stats are from conftest.py

def test_get_user_stats_no_climbs(auth_client, user1_fixture, app): # user1_fixture is the User object
    # Ensure no climbs for this user (clean state for this test aspect)
    with app.app_context():
        UserAttempt.query.filter_by(user_id=user1_fixture.id).delete()
        db.session.commit()

    response = auth_client.get(f'/users/{user1_fixture.id}/stats')
    assert response.status_code == 200
    stats = response.json
    assert stats['user_id'] == user1_fixture.id
    assert stats['username'] == user1_fixture.username
    assert stats['total_completed_unique_climbs'] == 0
    assert stats['highest_grade_completed'] == "N/A"
    assert stats['completed_grade_distribution'] == {}

def test_get_user_stats_basic_climbs(auth_client, user1_fixture, create_block_db, log_completed_climb_for_stats, app):
    # Clean relevant UserAttempt state for user1_fixture before this test
    with app.app_context():
        UserAttempt.query.filter_by(user_id=user1_fixture.id).delete()
        db.session.commit()

    # Create blocks with different difficulties
    b1_v1 = create_block_db(name="Stats Block V1", difficulty="V1", uploader_id=user1_fixture.id)
    b2_v2 = create_block_db(name="Stats Block V2", difficulty="V2", uploader_id=user1_fixture.id)
    b3_v1 = create_block_db(name="Stats Block V1 Again", difficulty="V1", uploader_id=user1_fixture.id)

    # Log completed climbs for user1
    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b1_v1.id)
    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b2_v2.id)
    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b1_v1.id) # Log b1_v1 again (not unique attempt for stats)
    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b3_v1.id) # Log a different V1

    response = auth_client.get(f'/users/{user1_fixture.id}/stats')
    assert response.status_code == 200
    stats = response.json

    assert stats['total_completed_unique_climbs'] == 3 # b1_v1, b2_v2, b3_v1
    assert stats['highest_grade_completed'] == "V2"
    assert stats['completed_grade_distribution'] == {
        "V1": 2, # b1_v1 and b3_v1 are unique V1s
        "V2": 1
    }

def test_get_user_stats_highest_grade_logic(auth_client, user1_fixture, create_block_db, log_completed_climb_for_stats, app):
    with app.app_context(): # Clean previous attempts for this user
        UserAttempt.query.filter_by(user_id=user1_fixture.id).delete()
        db.session.commit()

    b_v5 = create_block_db(name="Stats Block V5", difficulty="V5", uploader_id=user1_fixture.id)
    b_v3 = create_block_db(name="Stats Block V3", difficulty="V3", uploader_id=user1_fixture.id)
    b_vb = create_block_db(name="Stats Block VB", difficulty="VB", uploader_id=user1_fixture.id)

    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b_v3.id)
    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b_vb.id)
    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b_v5.id)

    response = auth_client.get(f'/users/{user1_fixture.id}/stats')
    assert response.status_code == 200
    assert response.json['highest_grade_completed'] == "V5"

def test_get_user_stats_unknown_grade(auth_client, user1_fixture, create_block_db, log_completed_climb_for_stats, app):
    with app.app_context(): # Clean previous attempts
        UserAttempt.query.filter_by(user_id=user1_fixture.id).delete()
        db.session.commit()

    b_unknown = create_block_db(name="Stats Block Unknown", difficulty="VTestUnknown", uploader_id=user1_fixture.id)
    log_completed_climb_for_stats(user_id=user1_fixture.id, block_id=b_unknown.id)

    response = auth_client.get(f'/users/{user1_fixture.id}/stats')
    assert response.status_code == 200
    assert response.json['highest_grade_completed'] == "N/A"
    assert response.json['completed_grade_distribution'] == {"VTestUnknown": 1}


def test_get_user_stats_permissions_admin_can_view(admin_client, user1_fixture):
    # user1_fixture is a regular user. Admin is viewing their stats.
    response = admin_client.get(f'/users/{user1_fixture.id}/stats')
    assert response.status_code == 200
    assert response.json['user_id'] == user1_fixture.id

def test_get_user_stats_permissions_non_admin_cannot_view_others(auth_client, client, app, user1_fixture):
    # user1_fixture is logged in via auth_client.
    # Create user2.
    user2_username = 'stats_user2'
    user2_email = 'stats_user2@example.com'

    # Use a generic client to create user2 to avoid session interference
    reg_res = create_test_user(client, user2_username, user2_email)
    assert reg_res.status_code == 201 # Ensure user is created

    user2_id = None
    with app.app_context():
        user2 = User.query.filter_by(email=user2_email).first()
        assert user2 is not None, "User2 creation failed or not found"
        user2_id = user2.id

    # auth_client (user1) tries to get user2's stats
    response = auth_client.get(f'/users/{user2_id}/stats')
    assert response.status_code == 403

def test_get_user_stats_nonexistent_user(auth_client): # Using auth_client, could be admin_client too
    response = auth_client.get('/users/999999/stats')
    assert response.status_code == 403 # Non-admin user trying to access non-existent user's stats (auth check first)

def test_get_user_stats_nonexistent_user_as_admin(admin_client):
    response = admin_client.get('/users/999999/stats')
    assert response.status_code == 404 # Admin can try, but user not found
    assert response.json['error'] == 'User not found.'
