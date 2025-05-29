import uuid # Added
import uuid # Added
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
    comments = db.relationship('Comment', backref='author', lazy='dynamic')
    push_subscriptions = db.relationship('PushSubscription', backref='user', lazy='dynamic') # Added

    # 'followed' relationship: users that this user is following
    followed = db.relationship(
        'User', secondary='user_follows', # Use string name of the table
        primaryjoin=lambda: (User.id == user_follows.c.follower_id),
        secondaryjoin=lambda: (User.id == user_follows.c.followed_id),
        backref=db.backref('followers', lazy='dynamic'), # 'followers' are users following this user
        lazy='dynamic'
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

# Association table for User follows
user_follows = db.Table('user_follows',
    db.Column('follower_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('followed_id', db.Integer, db.ForeignKey('user.id'), primary_key=True), # Corrected definition
    db.Column('timestamp', db.DateTime, default=datetime.utcnow)
)

# Association table for ClimbingBlock and Tag many-to-many relationship
block_tags = db.Table('block_tags',
    db.Column('block_id', db.Integer, db.ForeignKey('climbing_block.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False) # Tag names are unique

    def __repr__(self):
        return f'<Tag {self.name}>'

class ClimbingBlock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()), index=True) # Added
    name = db.Column(db.String(100), nullable=False)
    difficulty = db.Column(db.String(50), nullable=False)
    photo_filename = db.Column(db.String(200), nullable=True)
    highlight_data = db.Column(db.Text, nullable=True)
    uploader_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    attempts = db.relationship('UserAttempt', backref='block', lazy=True)
    tags = db.relationship('Tag', secondary=block_tags, lazy='subquery',
                           backref=db.backref('blocks', lazy=True))
    comments = db.relationship('Comment', backref='commented_block', lazy='dynamic')

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

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    block_id = db.Column(db.Integer, db.ForeignKey('climbing_block.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<Comment {self.id} by User {self.user_id} on Block {self.block_id}>'

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_url = db.Column(db.String(255), nullable=True)
    criteria = db.Column(db.Text, nullable=True) # Textual or JSON criteria

    def __repr__(self):
        return f'<Badge {self.name}>'

class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    earned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('earned_badges_assoc', lazy='dynamic'))
    badge = db.relationship('Badge', backref=db.backref('earned_by_users_assoc', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'badge_id', name='uq_user_badge'),)

    def __repr__(self):
        return f'<UserBadge User {self.user_id} earned Badge {self.badge_id} at {self.earned_at}>'

class Badge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    icon_url = db.Column(db.String(255), nullable=True)
    criteria = db.Column(db.Text, nullable=True) # Textual or JSON criteria

    def __repr__(self):
        return f'<Badge {self.name}>'

class UserBadge(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    badge_id = db.Column(db.Integer, db.ForeignKey('badge.id'), nullable=False)
    earned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('earned_badges_assoc', lazy='dynamic'))
    badge = db.relationship('Badge', backref=db.backref('earned_by_users_assoc', lazy='dynamic'))

    __table_args__ = (db.UniqueConstraint('user_id', 'badge_id', name='uq_user_badge'),)

    def __repr__(self):
        return f'<UserBadge User {self.user_id} earned Badge {self.badge_id} at {self.earned_at}>'

class PushSubscription(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subscription_json = db.Column(db.Text, nullable=False) # Stores the JSON string
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # user relationship is defined by the backref in User model

    def __repr__(self):
        return f'<PushSubscription {self.id} for User {self.user_id}>'
