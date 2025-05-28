# tests/test_blocks.py
import io

def test_create_block_without_photo(auth_client):
    response = auth_client.post('/blocks/', data={
        'name': 'Test Block 1', 'difficulty': 'V1'
    })
    assert response.status_code == 201
    assert response.json['block']['name'] == 'Test Block 1' # Adjusted to match actual response structure

def test_create_block_with_photo(auth_client):
    data = {
        'name': 'Test Block Photo',
        'difficulty': 'V2',
        'highlight_data': '{"holds": "some_data"}',
    }
    # Simulate file upload
    data['photo'] = (io.BytesIO(b"fakeimgbytes"), 'test.jpg')

    response = auth_client.post('/blocks/', data=data, content_type='multipart/form-data')
    assert response.status_code == 201
    assert response.json['block']['name'] == 'Test Block Photo' # Adjusted
    assert 'test.jpg' in response.json['block']['photo_url'] # Adjusted

def test_get_all_blocks(client): # No auth needed for listing
    response = client.get('/blocks/')
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_get_specific_block(auth_client):
    # First create a block to retrieve
    res_create = auth_client.post('/blocks/', data={'name': 'Specific Block', 'difficulty': 'V3'})
    assert res_create.status_code == 201 # Ensure block creation was successful
    block_id = res_create.json['block']['id'] # Adjusted

    response = auth_client.get(f'/blocks/{block_id}')
    assert response.status_code == 200
    assert response.json['name'] == 'Specific Block'
