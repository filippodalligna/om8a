# tests/test_badges.py
import pytest
from app.models.models import Badge, UserBadge, User, db # Adjust import
from datetime import datetime

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
