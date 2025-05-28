import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
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


    from app.routes.auth import bp as auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')

    from app.routes.blocks import bp as blocks_bp
    app.register_blueprint(blocks_bp, url_prefix='/blocks')

    from app.routes.history import bp as history_bp
    app.register_blueprint(history_bp, url_prefix='/history')

    from app.routes.leaderboard import bp as leaderboard_bp
    app.register_blueprint(leaderboard_bp, url_prefix='/leaderboard')

    return app
