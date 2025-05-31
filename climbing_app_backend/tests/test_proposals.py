# tests/test_proposals.py
import pytest
import io
import os # For potential file path checking, though can be optional
from app.models.models import BlockProposal, User, db # Adjust import if models are elsewhere
from flask import current_app # For accessing config for upload folder path

# Assuming auth_client and user1_fixture are from conftest.py

def test_submit_block_proposal_no_photo(auth_client, user1_fixture):
    data = {
        'location_description': 'Under the old bridge, by the river.',
        'climb_description': 'Starts on two crimps, big move to a sloper.',
        'proposed_grade': 'V4'
    }
    response = auth_client.post('/proposals/', data=data) # content_type will be multipart/form-data by default with data
    assert response.status_code == 201
    json_data = response.json['proposal']
    assert json_data['location_description'] == data['location_description']
    assert json_data['proposer_id'] == user1_fixture.id
    assert json_data['status'] == 'pending'
    assert json_data['photo_filename_proposal'] is None

    with auth_client.application.app_context():
        proposal = BlockProposal.query.get(json_data['id'])
        assert proposal is not None
        assert proposal.proposer_id == user1_fixture.id

def test_submit_block_proposal_with_photo(auth_client, user1_fixture):
    data = {
        'location_description': 'Cave system, main wall.',
        'climb_description': 'Dyno start, technical finish.',
        'proposed_grade': 'V6',
        'photo_proposal': (io.BytesIO(b"fake_proposal_image_bytes"), 'test_proposal.jpg')
    }
    response = auth_client.post('/proposals/', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    json_data = response.json['proposal']
    assert json_data['location_description'] == data['location_description']
    assert json_data['photo_filename_proposal'] is not None
    # Filename will have a UUID prefix, so check if 'test_proposal.jpg' (or part of it) is in the name
    assert 'test_proposal' in json_data['photo_filename_proposal']
    assert json_data['photo_filename_proposal'].endswith('.jpg')

    # Optional: Check if file exists (more of an integration test for file saving)
    # This requires current_app to be available or app context from auth_client
    app = auth_client.application
    photo_path = os.path.join(app.instance_path, app.config['PROPOSAL_UPLOAD_FOLDER'], json_data['photo_filename_proposal'])
    assert os.path.exists(photo_path)
    # Cleanup the created file
    if os.path.exists(photo_path):
        os.remove(photo_path)


def test_submit_block_proposal_missing_location(auth_client):
    data = {'climb_description': 'A climb.'}
    response = auth_client.post('/proposals/', data=data)
    assert response.status_code == 400 # Bad Request due to missing required field
    # Based on my route implementation, the error message is simpler
    assert 'Location description is required' in response.json['error']

def test_list_my_proposals(auth_client, user1_fixture, app): # Added app fixture
    # Clean up existing proposals for this user to ensure count is predictable
    with app.app_context():
        BlockProposal.query.filter_by(proposer_id=user1_fixture.id).delete()
        db.session.commit()

    # Submit a proposal first
    post_response = auth_client.post('/proposals/', data={'location_description': 'My Test Proposal Spot'})
    assert post_response.status_code == 201 # Ensure proposal was created

    response = auth_client.get('/proposals/me?per_page=5')
    assert response.status_code == 200
    json_data = response.json
    assert json_data['total_proposals'] == 1
    assert len(json_data['proposals']) == 1
    # Check if one of the proposals was made by user1_fixture
    assert json_data['proposals'][0]['proposer_id'] == user1_fixture.id
    assert json_data['proposals'][0]['location_description'] == 'My Test Proposal Spot'

def test_get_proposal_photo(auth_client):
    # 1. Submit proposal with photo
    filename_core = 'photo_to_serve'
    filename_ext = 'jpg'
    file_content = b"servemebytes"

    data = {
        'location_description': 'Photo serving test spot',
        'photo_proposal': (io.BytesIO(file_content), f"{filename_core}.{filename_ext}")
    }
    res_post = auth_client.post('/proposals/', data=data, content_type='multipart/form-data')
    assert res_post.status_code == 201
    saved_filename = res_post.json['proposal']['photo_filename_proposal']
    assert filename_core in saved_filename
    assert saved_filename.endswith(f".{filename_ext}")


    # 2. Attempt to GET the photo
    response = auth_client.get(f'/proposals/uploads/{saved_filename}')
    assert response.status_code == 200
    # Mimetype check can be tricky if server doesn't explicitly set it based on extension or content
    # For common image types, Flask's send_from_directory usually gets it right.
    # assert response.mimetype == 'image/jpeg' # This can be too specific if .jpg vs .jpeg matters or if content sniffing is off
    assert response.content_type.startswith('image/') # More robust check for image types
    assert response.data == file_content

    # Cleanup the created file
    app = auth_client.application
    photo_path = os.path.join(app.instance_path, app.config['PROPOSAL_UPLOAD_FOLDER'], saved_filename)
    if os.path.exists(photo_path):
        os.remove(photo_path)
