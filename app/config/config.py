# app/config.py
import os
from datetime import timedelta

class Config:
    """Base configuration."""
    # It's also better to use a static SECRET_KEY for Flask sessions etc. during dev
    SECRET_KEY = os.getenv('SECRET_KEY', 'a-default-flask-secret-key-change-me') # Use a static default
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'
    DATABASE_PATH = os.path.join(os.getcwd(), 'instance', 'chatgpt_clone.db')

    # JWT Settings
    # --- THIS IS THE IMPORTANT CHANGE ---
    # Use a static string directly for development if the env var isn't set.
    # Make this a complex, hard-to-guess string.
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-super-secret-and-static-jwt-key-here-change-me')
    # ------------------------------------
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_DEBUG = 1
    # You can override JWT_SECRET_KEY here too if needed, but inheriting is fine

class TestingConfig(Config):
    TESTING = True
    DATABASE_PATH = ':memory:'
    # Usually good to set a known secret key for tests too
    JWT_SECRET_KEY = 'test-jwt-secret-key'

class ProductionConfig(Config):
    DEBUG = False
    FLASK_DEBUG = 0
    # In production, strongly prefer getting keys from environment variables
    SECRET_KEY = os.environ['SECRET_KEY'] # Fail if not set
    JWT_SECRET_KEY = os.environ['JWT_SECRET_KEY'] # Fail if not set
    # Production DB could be configured differently here

# Configuration mapping for easy selection
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}