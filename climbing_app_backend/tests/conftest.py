import pytest
import os
from app import create_app, db # Assuming 'app' is the package name

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    # Ensure instance_path is correctly set if UPLOAD_FOLDER relies on it
    # For testing, UPLOAD_FOLDER might need to be a temporary directory
    
    # Determine the absolute path for the instance folder for tests
    # This assumes tests are run from the project root 'climbing_app_backend'
    project_root = os.path.abspath(os.path.dirname(os.path.dirname(__file__))) # This gets climbing_app_backend folder
    instance_path = os.path.join(project_root, 'tests', 'test_instance')
    
    # Create a specific test upload folder within the test instance path
    test_upload_folder_name = 'test_uploads'
    test_upload_folder_abs_path = os.path.join(instance_path, test_upload_folder_name)

    app = create_app(config_overrides={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{os.path.join(instance_path, "test_app.db")}', # Use file-based SQLite in test_instance
        'LOGIN_DISABLED': False, # Ensure login is not disabled for auth tests
        'WTF_CSRF_ENABLED': False, # Disable CSRF for simpler form testing if forms were used
        'UPLOAD_FOLDER': test_upload_folder_name, # Relative to instance_path
        'SERVER_NAME': 'localhost.test' # Common for testing, helps with url_for
    })
    
    # Ensure the instance path for the app object matches our desired test instance path
    app.instance_path = instance_path

    # Ensure test instance and upload folders exist
    if not os.path.exists(app.instance_path):
        os.makedirs(app.instance_path)
    if not os.path.exists(test_upload_folder_abs_path):
        os.makedirs(test_upload_folder_abs_path)

    with app.app_context():
        db.create_all() # Create all database tables

    yield app # provide the fixture value

    with app.app_context():
        db.drop_all() # Drop all database tables after test session
    
    # Clean up test instance folder
    # import shutil
    # shutil.rmtree(instance_path, ignore_errors=True)


@pytest.fixture()
def client(app):
    """A test client for the app."""
    return app.test_client()

@pytest.fixture()
def runner(app):
    """A test CLI runner for the app."""
    return app.test_cli_runner()

# Fixture to create a new user and log them in
@pytest.fixture
def auth_client(client):
    # Helper class or function to manage auth state
    class AuthActions:
        def __init__(self, client):
            self._client = client
            self._user_credentials = {} # To store credentials for potential reuse in a test

        def register(self, username='testuser', email='test@example.com', password='password'):
            self._user_credentials[email] = password # Store for login
            return self._client.post('/auth/register', json={
                'username': username,
                'email': email,
                'password': password
            })

        def login(self, email='test@example.com', password=None):
            # If password not provided, try to use stored one from registration
            if password is None:
                password = self._user_credentials.get(email, 'password')
            
            return self._client.post('/auth/login', json={
                'email': email,
                'password': password
            })

        def logout(self):
            return self._client.post('/auth/logout')

    # Register and login a default user for convenience in other tests
    auth = AuthActions(client)
    auth.register(username='defaultuser', email='default@example.com', password='password')
    auth.login(email='default@example.com') # Login as the default user
    
    # Make auth actions available to tests if they need to register/login other users
    client.auth = auth 
    return client # now the client has session cookies for an authenticated user

@pytest.fixture
def create_block(auth_client):
    """Fixture to create a block using the API, returns the block's JSON response."""
    def _create_block(name='Test Block for Comments', difficulty='V0'):
        response = auth_client.post('/blocks/', data={'name': name, 'difficulty': difficulty})
        # Ensure the response indicates success; adjust status code if your API differs
        assert response.status_code == 201, f"Failed to create block: {response.json}"
        return response.json['block'] # Assuming block details are under 'block' key
    return _create_block

@pytest.fixture(scope='function')
def user1_fixture(app, auth_client): # Added app fixture to ensure context
    # auth_client is already logged in as a user (typically user_id=1, email='default@example.com')
    # Return the User object for this user
    with app.app_context(): # Use the app fixture for context
        from app.models.models import User # Import here to avoid circular dependency issues
        user = User.query.filter_by(email='default@example.com').first()
        if not user:
            # Fallback if the default user from auth_client isn't found by that email
            # This might happen if auth_client's details change or it's the very first user (ID 1)
            user = User.query.get(1) 
        if not user:
            # If still not found, it's an issue with the auth_client setup or test DB state
            pytest.skip("Default user for auth_client (default@example.com or ID 1) not found. Check conftest.py's auth_client setup.")
        return user

# Helper functions for creating/logging in test users, moved from test_users.py
def create_test_user(client, username, email, password='password'):
    """Helper to register a new user via API for testing."""
    return client.post('/auth/register', json={
        'username': username, 'email': email, 'password': password
    })

def login_test_user(client, email, password='password'):
    """Helper to log in a user via API for testing."""
    return client.post('/auth/login', json={'email': email, 'password': password})

@pytest.fixture
def create_block_db(app): # Moved from test_badges.py to be globally available
    """Fixture to create a block directly in the DB."""
    def _create_block_db(name, difficulty, uploader_id=1): # Assuming default uploader_id 1 for simplicity
        from app.models.models import ClimbingBlock # Import here to avoid circularity
        with app.app_context():
            # Ensure uploader_id user exists or handle appropriately
            # For now, assume uploader_id=1 (default user from auth_client) exists
            block = ClimbingBlock(name=name, difficulty=difficulty, uploader_id=uploader_id)
            # uuid will be auto-generated by model default
            db.session.add(block)
            db.session.commit()
            return block
    return _create_block_db
