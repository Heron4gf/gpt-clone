# app/config.py
import os
from datetime import timedelta

class Config:
    """Base configuration."""
    SECRET_KEY = os.getenv('SECRET_KEY', os.urandom(24))
    STATIC_FOLDER = 'static'
    TEMPLATES_FOLDER = 'templates'
    DATABASE_PATH = os.path.join(os.getcwd(), 'instance', 'chatgpt_clone.db')
    
    # JWT Settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', os.urandom(24))
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)

class DevelopmentConfig(Config):
    DEBUG = True
    FLASK_DEBUG = 1

class TestingConfig(Config):
    TESTING = True
    DATABASE_PATH = ':memory:'

class ProductionConfig(Config):
    DEBUG = False
    FLASK_DEBUG = 0
    # Production DB could be configured differently here

# Configuration mapping for easy selection
config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
