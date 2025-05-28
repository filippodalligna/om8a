# tests/test_auth.py
def test_register(client):
    response = client.post('/auth/register', json={
        'username': 'newuser', 'email': 'new@example.com', 'password': 'password'
    })
    assert response.status_code == 201
    assert response.json['message'] == 'User registered successfully'

def test_login(client):
    # First, register a user to ensure they exist
    client.post('/auth/register', json={
        'username': 'loginuser', 'email': 'login@example.com', 'password': 'password'
    })
    response = client.post('/auth/login', json={
        'email': 'login@example.com', 'password': 'password'
    })
    assert response.status_code == 200
    assert response.json['message'] == 'Login successful'
    # Logout to clean up session for other tests
    client.post('/auth/logout')


def test_logout(auth_client): # Uses the pre-authenticated client
    response = auth_client.post('/auth/logout')
    assert response.status_code == 200
    assert response.json['message'] == 'Logout successful'

    # Verify user is logged out (e.g. accessing a protected route)
    response = auth_client.get('/history/me') # Example protected route
    assert response.status_code == 401 # Unauthorized
