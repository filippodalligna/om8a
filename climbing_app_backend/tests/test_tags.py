# tests/test_tags.py
import pytest
from app.models.models import Tag, db # Adjusted for direct db access if needed for verification

def test_create_tag(auth_client):
    response = auth_client.post('/tags/', json={'name': 'Overhang'})
    assert response.status_code == 201
    assert response.json['tag']['name'] == 'overhang' # My API returns {'tag': {'id': ..., 'name': ...}}
    tag = Tag.query.filter_by(name='overhang').first()
    assert tag is not None
    assert tag.name == 'overhang'

def test_create_duplicate_tag(auth_client):
    # Ensure the tag is created the first time
    response1 = auth_client.post('/tags/', json={'name': 'Slab'})
    assert response1.status_code == 201 # Or 409 if it somehow existed from another test (unlikely with test DB setup)

    # Attempt to create the same tag again
    response2 = auth_client.post('/tags/', json={'name': 'Slab'})
    assert response2.status_code == 409 # Conflict
    assert 'message' in response2.json
    assert response2.json['message'] == 'Tag already exists' # Based on my tags.py implementation

def test_list_tags(client, auth_client): # Added auth_client to create tags
    # Create some tags to ensure the list is not empty
    tag1_res = auth_client.post('/tags/', json={'name': 'Dynamic'})
    assert tag1_res.status_code == 201
    tag2_res = auth_client.post('/tags/', json={'name': 'Static'})
    assert tag2_res.status_code == 201

    response = client.get('/tags/') # Listing tags does not require auth
    assert response.status_code == 200
    assert isinstance(response.json, list)

    tag_names = [tag['name'] for tag in response.json]
    assert 'dynamic' in tag_names
    assert 'static' in tag_names

    # Check for at least two tags, could be more if other tests created some
    # and DB is not perfectly clean between tests (though it should be with session-scoped app fixture)
    assert len(response.json) >= 2

def test_create_tag_empty_name(auth_client):
    response = auth_client.post('/tags/', json={'name': '  '}) # Empty or whitespace only
    assert response.status_code == 400
    assert response.json['message'] == 'Tag name cannot be empty'

def test_create_tag_missing_name_field(auth_client):
    response = auth_client.post('/tags/', json={}) # Missing 'name' field
    assert response.status_code == 400
    assert response.json['message'] == 'Tag name is required'
