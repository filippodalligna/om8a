import os
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_babel import Babel # Added
from config import Config

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    # Since the user_id is just the primary key of our user table,
    # use it in the query for the user
    from app.models.models import User
    return User.query.get(int(user_id))

def create_app(config_class=Config, config_overrides=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    if config_overrides:
        app.config.update(config_overrides)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)

    # Initialize Babel
    babel = Babel(app)
    app.config['LANGUAGES'] = ['it', 'en']
    app.config['BABEL_DEFAULT_LOCALE'] = 'it'

    @babel.localeselector
    def get_locale():
        return request.accept_languages.best_match(app.config['LANGUAGES'])

    # Ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # Ensure the upload folder exists in the instance path
    # UPLOAD_FOLDER is defined as 'uploads' in config.py, relative to instance_path
    upload_folder_path = os.path.join(app.instance_path, app.config['UPLOAD_FOLDER'])
    try:
        os.makedirs(upload_folder_path, exist_ok=True)
    except OSError as e:
        # Handle error if needed, e.g., log it
        print(f"Error creating upload folder: {e}")
        pass

    # Ensure the proposal upload folder exists in the instance path
    proposal_upload_folder_config = app.config.get('PROPOSAL_UPLOAD_FOLDER', 'proposal_uploads') # Default if not in config
    proposal_upload_folder_path = os.path.join(app.instance_path, proposal_upload_folder_config)
    try:
        os.makedirs(proposal_upload_folder_path, exist_ok=True)
    except OSError as e:
        app.logger.error(f"Error creating proposal upload folder: {e}") # Use app.logger
        pass


    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.blocks import bp as blocks_bp
    app.register_blueprint(blocks_bp, url_prefix='/blocks')

    from app.routes.history import bp as history_bp
    app.register_blueprint(history_bp, url_prefix='/history')

    from app.routes.leaderboard import bp as leaderboard_bp
    app.register_blueprint(leaderboard_bp, url_prefix='/leaderboard')

    from app.routes.tags import tags_bp # Changed from bp to tags_bp to match definition
    app.register_blueprint(tags_bp) # url_prefix is defined in the blueprint itself

    from app.routes.comments import comments_bp # Added
    app.register_blueprint(comments_bp) # url_prefix is defined in the blueprint itself

    from app.routes.users import users_bp # Added
    app.register_blueprint(users_bp) # url_prefix is defined in the blueprint itself

    from app.routes.badges import badges_bp # Added
    app.register_blueprint(badges_bp) # url_prefix is defined in the blueprint itself

    from app.routes.notifications import notifications_bp # Added
    app.register_blueprint(notifications_bp) # url_prefix is defined in the blueprint itself

    from app.routes.admin import admin_bp # Added
    app.register_blueprint(admin_bp) # url_prefix is defined in the blueprint itself (/admin)

    from app.routes.proposals import proposals_bp # Added proposals_bp
    app.register_blueprint(proposals_bp) # url_prefix is /proposals (defined in proposals.py)

    return app
