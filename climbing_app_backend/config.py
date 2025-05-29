import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///../instance/app.db' # This path is relative to the app folder.
                                     # For instance folder, it's usually app.instance_path
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    UPLOAD_FOLDER = 'uploads' # Will be joined with app.instance_path

    # VAPID keys for Push Notifications (Worker: Using placeholders)
    VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY') or "YOUR_GENERATED_PRIVATE_KEY_PLACEHOLDER"
    VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY') or "YOUR_GENERATED_PUBLIC_KEY_PLACEHOLDER"
    VAPID_CLAIMS = {"sub": "mailto:admin@example.com"} # Replace with your admin email
