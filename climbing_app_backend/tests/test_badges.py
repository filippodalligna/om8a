# tests/test_badges.py
import pytest
import io
from app.models.models import Badge, UserBadge, User, db, Comment, UserAttempt, ClimbingBlock
from app.services.badge_service import PREDEFINED_BADGES, BADGE_FIRST_COMMENT, BADGE_FIRST_COMPLETED_CLIMB, BADGE_BLOCK_UPLOADER, BADGE_DIFFICULTY_MASTER_V3, BADGE_WEEKLY_SENDER_3 # Updated imports
from datetime import datetime, timedelta # Added timedelta

# Helper fixture to create a badge directly in the DB for testing purposes
@pytest.fixture
def create_badge_direct(app):
    def _create_badge(name, description="Test Desc", icon_url=None, criteria="Test Criteria"):
        with app.app_context():
            badge = Badge.query.filter_by(name=name).first() # Check if badge already exists
            if badge:
                return badge # Return existing badge to avoid unique constraint errors
            badge = Badge(name=name, description=description, icon_url=icon_url, criteria=criteria)
            db.session.add(badge)
            db.session.commit()
            return badge
    return _create_badge

# Helper fixture to create a UserBadge entry directly in the DB
@pytest.fixture
def assign_badge_to_user_direct(app, create_badge_direct):
    def _assign(user_id, badge_name, earned_at=None):
        with app.app_context():
            badge = Badge.query.filter_by(name=badge_name).first()
            if not badge:
                badge = create_badge_direct(name=badge_name) # Create if doesn't exist for test simplicity

            # Check if this UserBadge association already exists
            user_badge = UserBadge.query.filter_by(user_id=user_id, badge_id=badge.id).first()
            if user_badge:
                if earned_at: # Update earned_at if provided and different
                    user_badge.earned_at = earned_at
            else: # Create new association
                user_badge = UserBadge(user_id=user_id, badge_id=badge.id)
                if earned_at:
                    user_badge.earned_at = earned_at

            db.session.add(user_badge) # Add or re-add to session if updated
            db.session.commit()
            return user_badge
    return _assign


def test_list_all_badges(client, create_badge_direct):
    create_badge_direct(name="FirstClimb", description="Completed your first climb")
    create_badge_direct(name="V5Conqueror", description="Completed a V5 climb")

    response = client.get('/badges/') # No auth typically needed for listing badges
    assert response.status_code == 200

    # Filter out pre-existing badges from other tests if any by checking specific names
    response_data = response.json
    filtered_badges = [b for b in response_data if b['name'] in ["FirstClimb", "V5Conqueror"]]

    assert len(filtered_badges) >= 2 # Check if our created badges are present
    badge_names = [b['name'] for b in filtered_badges]
    assert "FirstClimb" in badge_names
    assert "V5Conqueror" in badge_names
    # Example of checking other fields for one of the badges
    first_climb_badge = next((b for b in filtered_badges if b['name'] == "FirstClimb"), None)
    assert first_climb_badge is not None
    assert first_climb_badge['description'] == "Completed your first climb"

def test_list_badges_empty(client, app): # Added app to clean up
    # Ensure a clean state for this specific test if needed
    with app.app_context():
        UserBadge.query.delete()
        Badge.query.delete()
        db.session.commit()

    response = client.get('/badges/')
    assert response.status_code == 200
    assert len(response.json) == 0


def test_list_user_earned_badges(client, user1_fixture, assign_badge_to_user_direct):
    # user1_fixture provides the User object for the default authenticated user (auth_client)
    user_id = user1_fixture.id

    assign_badge_to_user_direct(user_id=user_id, badge_name="SocialButterfly", earned_at=datetime.utcnow())
    assign_badge_to_user_direct(user_id=user_id, badge_name="EarlyBird")

    response = client.get(f'/badges/users/{user_id}/badges')
    assert response.status_code == 200
    assert len(response.json) == 2
    earned_badge_names = [b['name'] for b in response.json]
    assert "SocialButterfly" in earned_badge_names
    assert "EarlyBird" in earned_badge_names
    # Check earned_at timestamp format if important
    # Example: assert "earned_at" in response.json[0] and "Z" in response.json[0]["earned_at"]

def test_list_user_earned_badges_none(client, user1_fixture, app): # Added app to clean up
    user_id = user1_fixture.id # User exists but has no badges
    # Ensure no UserBadge entries for this user from previous tests
    with app.app_context():
        UserBadge.query.filter_by(user_id=user_id).delete()
        db.session.commit()

    response = client.get(f'/badges/users/{user_id}/badges')
    assert response.status_code == 200
    assert len(response.json) == 0

def test_list_badges_for_nonexistent_user(client):
    response = client.get('/badges/users/99999/badges') # User 99999 does not exist
    assert response.status_code == 404 # Assuming User.query.get_or_404(user_id) is used in the endpoint


# --- Tests for awarding badges ---

def test_award_badge_first_comment(auth_client, user1_fixture, create_block, app):
    block_json = create_block() # Create a block to comment on
    block_id = block_json['id']

    # Ensure user does not have the badge yet
    with app.app_context():
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_FIRST_COMMENT]["name"]).first()
        if badge_def: # Badge might not exist if this is the first time it's being awarded
            assert UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first() is None

    # Post the first comment
    auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'My first comment!'})

    # Verify badge is awarded
    with app.app_context():
        # _ensure_badge_exists would have created it if it wasn't there
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_FIRST_COMMENT]["name"]).first()
        assert badge_def is not None, "Badge definition should have been created"

        user_badge = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first()
        assert user_badge is not None
        assert user_badge.badge.name == PREDEFINED_BADGES[BADGE_FIRST_COMMENT]["name"]

    # Post a second comment - badge should not be awarded again
    auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'My second comment!'})
    with app.app_context():
        user_badges_count = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).count()
        assert user_badges_count == 1


def test_award_badge_first_completed_climb(auth_client, user1_fixture, create_block, app):
    block_json = create_block()
    block_id = block_json['id']

    # Record a 'tried' attempt first (should not award)
    auth_client.post('/history/attempts', json={
        'block_id': block_id, 'status': 'tried', 'personal_notes': 'Almost got it'
    })
    with app.app_context():
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_FIRST_COMPLETED_CLIMB]["name"]).first()
        if badge_def:
            assert UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first() is None

    # Record the first 'completed' attempt
    auth_client.post('/history/attempts', json={
        'block_id': block_id, 'status': 'completed', 'personal_notes': 'Sent it!'
    })
    with app.app_context():
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_FIRST_COMPLETED_CLIMB]["name"]).first()
        assert badge_def is not None
        user_badge = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first()
        assert user_badge is not None
        assert user_badge.badge.name == PREDEFINED_BADGES[BADGE_FIRST_COMPLETED_CLIMB]["name"]

    # Record another 'completed' attempt - badge should not be awarded again
    block2_json = create_block(name="Second Block")
    auth_client.post('/history/attempts', json={
        'block_id': block2_json['id'], 'status': 'completed', 'personal_notes': 'Another one!'
    })
    with app.app_context():
        user_badges_count = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).count()
        assert user_badges_count == 1


def test_award_badge_block_uploader_with_photo(auth_client, user1_fixture, app):
    # Upload a block with a photo
    data = {'name': 'Photo Block 1', 'difficulty': 'V1', 'photo': (io.BytesIO(b"fakeimage"), 'test.jpg')}
    auth_client.post('/blocks/', data=data, content_type='multipart/form-data')

    with app.app_context():
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_BLOCK_UPLOADER]["name"]).first()
        assert badge_def is not None
        user_badge = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first()
        assert user_badge is not None
        assert user_badge.badge.name == PREDEFINED_BADGES[BADGE_BLOCK_UPLOADER]["name"]

    # Upload another block with a photo - badge should not be awarded again
    data2 = {'name': 'Photo Block 2', 'difficulty': 'V2', 'photo': (io.BytesIO(b"anotherimage"), 'test2.jpg')}
    auth_client.post('/blocks/', data=data2, content_type='multipart/form-data')
    with app.app_context():
        user_badges_count = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).count()
        assert user_badges_count == 1


def test_badge_block_uploader_no_photo(auth_client, user1_fixture, app):
    # Upload a block without a photo
    auth_client.post('/blocks/', data={'name': 'NoPhoto Block', 'difficulty': 'V0'})

    with app.app_context():
        # Badge definition might be created by _ensure_badge_exists if any other test triggered it,
        # but it should not be awarded to this user.
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_BLOCK_UPLOADER]["name"]).first()
        if badge_def: # Only check UserBadge if Badge definition exists
            user_badge = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first()
            assert user_badge is None # Should NOT be awarded

# --- New fixtures and tests for advanced badges ---

@pytest.fixture
def create_block_db(app):
    def _create_block_db(name, difficulty, uploader_id=1): # Assuming default uploader
        with app.app_context():
            block = ClimbingBlock(name=name, difficulty=difficulty, uploader_id=uploader_id)
            # uuid will be auto-generated by model default
            db.session.add(block)
            db.session.commit()
            return block
    return _create_block_db

@pytest.fixture
def log_completed_climb(auth_client, user1_fixture): # user1_fixture here is implicitly used by auth_client
    def _log_completed_climb(block_id, recorded_at=None): # recorded_at not used by API version
        payload = {'block_id': block_id, 'status': 'completed'}
        return auth_client.post('/history/attempts', json=payload)
    return _log_completed_climb

@pytest.fixture
def log_completed_climb_direct_db(app, user1_fixture):
    def _log_climb(block_id, recorded_at_datetime):
        with app.app_context():
            attempt = UserAttempt(
                user_id=user1_fixture.id,
                block_id=block_id,
                status='completed',
                recorded_at=recorded_at_datetime
            )
            db.session.add(attempt)
            db.session.commit()
            # Manually trigger the badge check after direct DB manipulation
            # This ensures the service logic is tested with controlled data
            from app.services.badge_service import check_and_award_climbing_milestone_badges
            block = ClimbingBlock.query.get(block_id)
            if block:
                 check_and_award_climbing_milestone_badges(user1_fixture.id, block_id, block.difficulty)
            return attempt
    return _log_climb


def test_award_badge_v3_master(user1_fixture, auth_client, create_block_db, log_completed_climb, app):
    # Create 3 unique V3 blocks
    block_v3_1 = create_block_db(name="V3 Block 1", difficulty="V3", uploader_id=user1_fixture.id)
    block_v3_2 = create_block_db(name="V3 Block 2", difficulty="V3", uploader_id=user1_fixture.id)
    block_v3_3 = create_block_db(name="V3 Block 3", difficulty="V3", uploader_id=user1_fixture.id)
    block_v2_1 = create_block_db(name="V2 Block 1", difficulty="V2", uploader_id=user1_fixture.id) # Non-V3

    # Log completions using API to trigger badge logic
    log_completed_climb(block_v3_1.id)
    log_completed_climb(block_v2_1.id) # This V2 climb should not count towards V3 master
    log_completed_climb(block_v3_2.id)

    # User should not have the badge yet (only 2 V3s)
    with app.app_context():
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_DIFFICULTY_MASTER_V3]["name"]).first()
        assert badge_def is not None # Should be ensured by service
        assert UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first() is None

    # Log the 3rd V3 climb
    log_completed_climb(block_v3_3.id)
    with app.app_context():
        user_badge = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first()
        assert user_badge is not None, "V3 Master badge should be awarded"
        assert user_badge.badge.name == PREDEFINED_BADGES[BADGE_DIFFICULTY_MASTER_V3]["name"]

    # Log a 4th V3 climb (same as 1st) - should not re-award or error, count for badge is based on distinct
    log_completed_climb(block_v3_1.id)
    with app.app_context():
        assert UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).count() == 1


def test_award_badge_weekly_sender_3(user1_fixture, auth_client, create_block_db, log_completed_climb_direct_db, app):
    today = datetime.utcnow()
    two_days_ago = today - timedelta(days=2)
    four_days_ago = today - timedelta(days=4)
    eight_days_ago = today - timedelta(days=8) # Outside 7-day window

    # Create blocks
    block1 = create_block_db(name="Weekly Block 1", difficulty="V1")
    block2 = create_block_db(name="Weekly Block 2", difficulty="V2")
    block3 = create_block_db(name="Weekly Block 3", difficulty="V3")
    block4 = create_block_db(name="Old Block", difficulty="V1")

    # Log climbs with specific dates using direct DB writes
    log_completed_climb_direct_db(block1.id, recorded_at_datetime=four_days_ago)
    log_completed_climb_direct_db(block2.id, recorded_at_datetime=two_days_ago)
    log_completed_climb_direct_db(block4.id, recorded_at_datetime=eight_days_ago) # Old climb

    # User should not have the badge yet (only 2 recent unique climbs recorded directly)
    with app.app_context():
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_WEEKLY_SENDER_3]["name"]).first()
        assert badge_def is not None
        assert UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first() is None

    # Log the 3rd recent unique climb via API to trigger the service logic
    response = auth_client.post('/history/attempts', json={'block_id': block3.id, 'status': 'completed'})
    assert response.status_code == 201

    with app.app_context():
        badge_def = Badge.query.filter_by(name=PREDEFINED_BADGES[BADGE_WEEKLY_SENDER_3]["name"]).first()
        assert badge_def is not None
        user_badge = UserBadge.query.filter_by(user_id=user1_fixture.id, badge_id=badge_def.id).first()
        assert user_badge is not None, "Weekly Sender badge should be awarded"
        assert user_badge.badge.name == PREDEFINED_BADGES[BADGE_WEEKLY_SENDER_3]["name"]
