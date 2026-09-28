import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    """SafeHer Application Configuration."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'safeher-secret-key-2026-super-secure')
    
    # Defaults to local SQLite for instant zero-configuration start.
    # Set DATABASE_URL=mysql+pymysql://username:password@localhost:3306/safeher_db to use MySQL.
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        f"sqlite:///{os.path.join(BASE_DIR, 'safeher.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Application Info
    APP_NAME = "SafeHer"
    APP_TAGLINE = "Smart Women Safety & Emergency Alert System"
    EMERGENCY_HOTLINE = "112"
    WOMEN_HELPLINE = "1091"
    POLICE_HELPLINE = "100"
    AMBULANCE_HELPLINE = "108"
