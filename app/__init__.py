# app/__init__.py
import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager

def create_app(config_name='development'):
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration
    from app.config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app)
    jwt = JWTManager(app)
    
    # Initialize database
    from app.utils.db import init_db, init_app as init_db_app
    with app.app_context():
        init_db()
    init_db_app(app)  # Register database teardown
    
    # Initialize OpenAI client
    from load_client import load_client, isClientLoaded
    if not isClientLoaded():
        load_client()
    
    # Register blueprints
    from app.routes.auth_routes import auth_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.user_routes import user_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    
    # Serve frontend at root route
    @app.route('/')
    def index():
        return app.send_static_file('index.html')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {"status": "healthy"}, 200
    
    return app
