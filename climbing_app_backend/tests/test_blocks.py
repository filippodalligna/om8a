# tests/test_blocks.py
import io
import pytest # Added for potential fixture use, though not strictly needed for these examples
from app.models.models import Tag, ClimbingBlock, db, Comment # Added Comment

def test_create_block_without_photo(auth_client):
    response = auth_client.post('/blocks/', data={
        'name': 'Test Block 1', 'difficulty': 'V1'
    })
    assert response.status_code == 201
    assert response.json['block']['name'] == 'Test Block 1'

def test_create_block_with_photo(auth_client):
    data = {
        'name': 'Test Block Photo',
        'difficulty': 'V2',
        'highlight_data': '{"holds": "some_data"}',
    }
    data['photo'] = (io.BytesIO(b"fakeimgbytes"), 'test.jpg')
    response = auth_client.post('/blocks/', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    assert response.json['block']['name'] == 'Test Block Photo'
    assert response.json['block']['photo_filename'] is not None # Check filename exists
    assert response.json['block']['photo_url'].endswith(response.json['block']['photo_filename'])


def test_get_all_blocks(client):
    response = client.get('/blocks/')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_get_specific_block(auth_client):
    # First create a block to retrieve
    res_create = auth_client.post('/blocks/', data={'name': 'Specific Block', 'difficulty': 'V3'})
    assert res_create.status_code == 201
    block_id = res_create.json['block']['id']

    response = auth_client.get(f'/blocks/{block_id}')
    assert response.status_code == 200
    assert response.json['name'] == 'Specific Block' # Assuming block detail response is flat JSON from previous implementation, adjust if needed

# --- Tests for block-tag associations ---

def test_add_tag_to_block_by_id(auth_client):
    # 1. Create a block
    block_res = auth_client.post('/blocks/', data={'name': 'Tagged Block 1', 'difficulty': 'V4'})
    assert block_res.status_code == 201
    block_id = block_res.json['block']['id']

    # 2. Create a tag
    tag_res = auth_client.post('/tags/', json={'name': 'Crimp'})
    assert tag_res.status_code == 201
    tag_id = tag_res.json['tag']['id'] # My API returns {'tag': {'id': ..., 'name': ...}}

    # 3. Add tag to block
    response = auth_client.post(f'/blocks/{block_id}/tags', json={'tag_id': tag_id})
    assert response.status_code == 200 
    assert response.json['message'] == 'Tag added to block'
    assert any(t['id'] == tag_id for t in response.json['tags'])

    # Optional: Verify by fetching the block (assuming GET /blocks/<id> returns tags)
    # This part requires that the GET /blocks/<id> endpoint is updated to serialize tags.
    # For now, we rely on the response from the POST /tags endpoint.
    # block_details_res = auth_client.get(f'/blocks/{block_id}')
    # assert block_details_res.status_code == 200
    # assert 'tags' in block_details_res.json # Ensure 'tags' key exists
    # assert any(t['id'] == tag_id for t in block_details_res.json.get('tags', []))


def test_add_tag_to_block_by_name_existing_tag(auth_client):
    block_res = auth_client.post('/blocks/', data={'name': 'Tagged Block Name 1', 'difficulty': 'V5'})
    assert block_res.status_code == 201
    block_id = block_res.json['block']['id']
    
    tag_res = auth_client.post('/tags/', json={'name': 'Sloper'}) # Ensure tag exists
    assert tag_res.status_code == 201
    # tag_id = tag_res.json['tag']['id'] # Not strictly needed for this test variant

    response = auth_client.post(f'/blocks/{block_id}/tags', json={'tag_name': 'Sloper'})
    assert response.status_code == 200
    assert response.json['message'] == 'Tag added to block'
    assert any(t['name'] == 'sloper' for t in response.json['tags'])


def test_add_tag_to_block_by_name_new_tag(auth_client):
    block_res = auth_client.post('/blocks/', data={'name': 'Tagged Block NewTag', 'difficulty': 'V6'})
    assert block_res.status_code == 201
    block_id = block_res.json['block']['id']

    response = auth_client.post(f'/blocks/{block_id}/tags', json={'tag_name': 'Jugs'}) # New tag
    assert response.status_code == 200
    assert response.json['message'] == 'Tag added to block'
    assert any(t['name'] == 'jugs' for t in response.json['tags'])
    
    # Verify the tag was created in the DB
    tag = Tag.query.filter_by(name='jugs').first()
    assert tag is not None
    assert tag.name == 'jugs'


def test_remove_tag_from_block(auth_client):
    # 1. Create block and tag, then associate them
    block_res = auth_client.post('/blocks/', data={'name': 'UntagMe Block', 'difficulty': 'V7'})
    assert block_res.status_code == 201
    block_id = block_res.json['block']['id']
    
    tag_res = auth_client.post('/tags/', json={'name': 'Pinch'})
    assert tag_res.status_code == 201
    tag_id = tag_res.json['tag']['id']
    
    add_res = auth_client.post(f'/blocks/{block_id}/tags', json={'tag_id': tag_id})
    assert add_res.status_code == 200 # Ensure association was successful
    assert any(t['id'] == tag_id for t in add_res.json['tags'])

    # 2. Remove the tag
    response = auth_client.delete(f'/blocks/{block_id}/tags/{tag_id}')
    assert response.status_code == 200 
    assert response.json['message'] == 'Tag removed from block'

    # Verify removal by checking the tags associated with the block
    # The remove endpoint in my implementation does not return the list of current tags.
    # So, we must fetch the block again or rely on the message.
    # For a more robust test, fetch the block and check its tags.
    # This requires GET /blocks/<id> to return tags.
    # block_details_res_after = auth_client.get(f'/blocks/{block_id}')
    # assert block_details_res_after.status_code == 200
    # assert 'tags' in block_details_res_after.json
    # assert not any(t['id'] == tag_id for t in block_details_res_after.json.get('tags', []))
    
    # Simpler check: try adding the same tag again, it should not report "already associated"
    reattempt_add_res = auth_client.post(f'/blocks/{block_id}/tags', json={'tag_id': tag_id})
    assert reattempt_add_res.status_code == 200 # Should be able to add it again
    assert any(t['id'] == tag_id for t in reattempt_add_res.json['tags'])


# --- Tests for filtering blocks by tags ---

def test_filter_blocks_by_one_tag(auth_client, client):
    # 1. Create tags
    tag1_res = auth_client.post('/tags/', json={'name': 'TagFilterAlpha'})
    assert tag1_res.status_code == 201
    tag1_id = tag1_res.json['tag']['id']

    # 2. Create blocks
    block1_res = auth_client.post('/blocks/', data={'name': 'Block Alpha', 'difficulty': 'V1'})
    assert block1_res.status_code == 201
    block1_id = block1_res.json['block']['id'] # My API returns block under 'block' key

    block2_res = auth_client.post('/blocks/', data={'name': 'Block Beta', 'difficulty': 'V1'})
    assert block2_res.status_code == 201
    block2_id = block2_res.json['block']['id']

    # 3. Associate tag1 with Block Alpha
    add_tag_res = auth_client.post(f'/blocks/{block1_id}/tags', json={'tag_id': tag1_id})
    assert add_tag_res.status_code == 200

    # 4. Get blocks filtered by 'TagFilterAlpha' (normalized to lowercase)
    response = client.get('/blocks/?tags=tagfilteralpha')
    assert response.status_code == 200
    block_ids = [b['id'] for b in response.json]
    assert block1_id in block_ids
    assert block2_id not in block_ids

def test_filter_blocks_by_multiple_tags(auth_client, client):
    # 1. Create tags
    tag_m1_res = auth_client.post('/tags/', json={'name': 'TagMultiCharlie'})
    assert tag_m1_res.status_code == 201
    tag_m1_id = tag_m1_res.json['tag']['id']

    tag_m2_res = auth_client.post('/tags/', json={'name': 'TagMultiDelta'})
    assert tag_m2_res.status_code == 201
    tag_m2_id = tag_m2_res.json['tag']['id']

    # 2. Create blocks
    block_m1_res = auth_client.post('/blocks/', data={'name': 'Block M-CharlieDelta', 'difficulty': 'V2'})
    assert block_m1_res.status_code == 201
    block_m1_id = block_m1_res.json['block']['id']

    block_m2_res = auth_client.post('/blocks/', data={'name': 'Block M-CharlieOnly', 'difficulty': 'V2'})
    assert block_m2_res.status_code == 201
    block_m2_id = block_m2_res.json['block']['id']
    
    block_m3_res = auth_client.post('/blocks/', data={'name': 'Block M-NoFilterTags', 'difficulty': 'V2'})
    assert block_m3_res.status_code == 201
    block_m3_id = block_m3_res.json['block']['id']


    # 3. Associate tags
    # Block M-CharlieDelta gets both tags
    add_tag1_m1_res = auth_client.post(f'/blocks/{block_m1_id}/tags', json={'tag_id': tag_m1_id})
    assert add_tag1_m1_res.status_code == 200
    add_tag2_m1_res = auth_client.post(f'/blocks/{block_m1_id}/tags', json={'tag_id': tag_m2_id})
    assert add_tag2_m1_res.status_code == 200
    
    # Block M-CharlieOnly gets only TagMultiCharlie
    add_tag1_m2_res = auth_client.post(f'/blocks/{block_m2_id}/tags', json={'tag_id': tag_m1_id})
    assert add_tag1_m2_res.status_code == 200

    # 4. Get blocks filtered by 'TagMultiCharlie,TagMultiDelta' (normalized)
    response = client.get('/blocks/?tags=tagmulticharlie,tagmultidelta')
    assert response.status_code == 200
    block_ids = [b['id'] for b in response.json]
    assert block_m1_id in block_ids  # Should have Block M-CharlieDelta
    assert block_m2_id not in block_ids # Should not have Block M-CharlieOnly
    assert block_m3_id not in block_ids # Should not have Block M-NoFilterTags

def test_filter_blocks_by_non_existent_tag(client):
    response = client.get('/blocks/?tags=nonexistenttag')
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) == 0 # Expect empty list

def test_filter_blocks_by_tag_no_matches(auth_client, client):
    # Create a tag that won't be associated with any blocks in this test
    tag_res = auth_client.post('/tags/', json={'name': 'UnusedFilterTag'})
    assert tag_res.status_code == 201
    
    # Create some blocks without this tag
    auth_client.post('/blocks/', data={'name': 'Block Epsilon', 'difficulty': 'V1'})
    auth_client.post('/blocks/', data={'name': 'Block Zeta', 'difficulty': 'V1'})

    response = client.get('/blocks/?tags=unusedfiltertag')
    assert response.status_code == 200
    assert isinstance(response.json, list)
    assert len(response.json) == 0

# --- Tests for comments on blocks ---

def test_post_comment_on_block(auth_client, create_block):
    block_json = create_block() # Uses the fixture from conftest.py
    block_id = block_json['id']
    
    response = auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'This is a test comment!'})
    assert response.status_code == 201
    assert response.json['comment']['text'] == 'This is a test comment!'
    assert response.json['comment']['block_id'] == block_id
    # Assuming 'defaultuser' is the one logged in by auth_client
    assert response.json['comment']['author_username'] == 'defaultuser' 

def test_post_comment_empty_text_on_block(auth_client, create_block):
    block_json = create_block()
    block_id = block_json['id']
    response = auth_client.post(f'/blocks/{block_id}/comments', json={'text': '   '})
    assert response.status_code == 400
    assert response.json['error'] == 'Comment text is required and cannot be empty' # Match API message

def test_post_comment_on_nonexistent_block(auth_client):
    response = auth_client.post('/blocks/99999/comments', json={'text': 'A comment'})
    assert response.status_code == 404 # Block not found

def test_get_comments_for_block(auth_client, client, create_block):
    block_json = create_block()
    block_id = block_json['id']

    # Post a few comments using auth_client
    comment1_res = auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'Comment 1'})
    assert comment1_res.status_code == 201
    comment2_res = auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'Comment 2'})
    assert comment2_res.status_code == 201

    # Use unauthenticated client to get comments, as GET /comments is public
    response = client.get(f'/blocks/{block_id}/comments')
    assert response.status_code == 200
    assert response.json['total_comments'] == 2
    assert len(response.json['comments']) == 2
    # Comments are ordered by newest first (descending created_at)
    assert response.json['comments'][0]['text'] == 'Comment 2' 
    assert response.json['comments'][1]['text'] == 'Comment 1'

def test_get_comments_for_block_pagination(auth_client, client, create_block):
    block_json = create_block()
    block_id = block_json['id']
    
    # Create 3 comments
    auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'Page Comment 1'}) # Oldest
    auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'Page Comment 2'})
    auth_client.post(f'/blocks/{block_id}/comments', json={'text': 'Page Comment 3'}) # Newest

    # Get page 1, 2 comments per page
    response = client.get(f'/blocks/{block_id}/comments?page=1&per_page=2')
    assert response.status_code == 200
    assert len(response.json['comments']) == 2
    assert response.json['total_comments'] == 3
    assert response.json['current_page'] == 1
    assert response.json['total_pages'] == 2
    assert response.json['comments'][0]['text'] == 'Page Comment 3' # Newest
    assert response.json['comments'][1]['text'] == 'Page Comment 2'

    # Get page 2, 2 comments per page
    response_page2 = client.get(f'/blocks/{block_id}/comments?page=2&per_page=2')
    assert response_page2.status_code == 200
    assert len(response_page2.json['comments']) == 1
    assert response_page2.json['total_comments'] == 3
    assert response_page2.json['current_page'] == 2
    assert response_page2.json['total_pages'] == 2
    assert response_page2.json['comments'][0]['text'] == 'Page Comment 1' # Oldest
