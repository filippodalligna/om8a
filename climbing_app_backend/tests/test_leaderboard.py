# tests/test_leaderboard.py
def test_get_leaderboard(client): # No auth needed
    response = client.get('/leaderboard/')
    assert response.status_code == 200
    assert isinstance(response.json, list)
    # Further assertions could check structure if data was pre-populated
