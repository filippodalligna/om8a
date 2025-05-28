from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    climber_blocks = db.relationship('ClimbingBlock', backref='uploader', lazy=True)
    attempts = db.relationship('UserAttempt', backref='user', lazy=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

class ClimbingBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    photo_filename = db.Column(db.String(200), nullable=True)
    highlight_data = db.Column(db.Text, nullable=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    attempts = db.relationship('UserAttempt', backref='block', lazy=True)

    def __repr__(self):
        return f'<ClimbingBlock {self.name}>'

class UserAttempt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    block_id = db.Column(db.Integer, db.ForeignKey('climbing_block.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False)  # e.g., 'tried', 'completed'
    attempts_count = db.Column(db.Integer, nullable=True)
    time_taken = db.Column(db.String(50), nullable=True)
    sensations = db.Column(db.Text, nullable=True)
    personal_notes = db.Column(db.Text, nullable=True)
    recorded_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserAttempt {self.user_id} - {self.block_id}>'
