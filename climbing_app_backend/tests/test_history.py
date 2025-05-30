# tests/test_history.py
def test_record_attempt(auth_client):
    # 1. Create a block first using the test client's auth capabilities
    # The auth_client fixture already has a default logged-in user.
    block_res = auth_client.post('/blocks/', data={'name': 'History Block', 'difficulty': 'V0'})
    assert block_res.status_code == 201
    # Assuming the block creation response structure is {'message': '...', 'block': {'id': ..., ...}}
    block_id = block_res.json['block']['id']

    # 2. Record an attempt
    response = auth_client.post('/history/attempts', json={
        'block_id': block_id, 'status': 'completed', 'personal_notes': 'fun!'
    })
    assert response.status_code == 201
    # Assuming the attempt response structure is {'message': '...', 'attempt': {'personal_notes': ..., 'block_details': {'name': ...}}}
    assert response.json['attempt']['personal_notes'] == 'fun!'
    assert response.json['attempt']['block_details']['name'] == 'History Block'


def test_get_my_history(auth_client):
    # Optional: Create an attempt first to ensure history is not empty
    block_res = auth_client.post('/blocks/', data={'name': 'My History Block', 'difficulty': 'V1'})
    assert block_res.status_code == 201
    block_id = block_res.json['block']['id']
    auth_client.post('/history/attempts', json={'block_id': block_id, 'status': 'tried'})

    response = auth_client.get('/history/me')
    assert response.status_code == 200
    assert isinstance(response.json, list)
    # Could add more assertions here, e.g., check if the recently added attempt is present
    if len(response.json) > 0:
        assert response.json[0]['block_name'] == 'My History Block' # Assuming history is ordered by recent first
        assert response.json[0]['status'] == 'tried'
