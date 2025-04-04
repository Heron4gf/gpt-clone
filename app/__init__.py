# app/__init__.py
import os
import logging
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

logger = logging.getLogger(__name__)

def create_app(config_name='development'):
    logger.info(f"Creating app with config: {config_name}")
    app = Flask(__name__, 
                template_folder='templates',
                static_folder='static')
    
    # Load configuration
    from app.config.config import config
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    CORS(app)
    jwt = JWTManager(app)
    
    # Initialize database
    from app.utils.db import init_db, init_app as init_db_app
    with app.app_context():
        logger.info("Initializing database")
        init_db()
    init_db_app(app)  # Register database teardown
    
    # Initialize OpenAI client
    try:
        logger.info("Loading OpenAI client")
        from load_client import load_client, isClientLoaded
        if not isClientLoaded():
            client = load_client()
            logger.info(f"OpenAI client loaded: {client is not None}")
        else:
            logger.info("OpenAI client already loaded")
    except Exception as e:
        logger.error(f"Error loading OpenAI client: {str(e)}", exc_info=True)
        logger.warning("Application will continue, but chat functionality may not work properly")
    
    # Configure JWT error handling
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({"error": "Authentication required"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({"error": "Invalid or expired token"}), 401
    
    # Register blueprints
    logger.info("Registering blueprints")
    from app.routes.auth_routes import auth_bp
    from app.routes.chat_routes import chat_bp
    from app.routes.user_routes import user_bp
    from app.routes.api_routes import api_bp
    from app.routes.model_routes import model_bp
    
    # Register the auth routes directly under /api instead of /api/auth
    # This ensures /api/login, /api/register, and /api/me are accessible
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp, url_prefix='/api/chat')
    app.register_blueprint(user_bp, url_prefix='/api/users')
    app.register_blueprint(api_bp, url_prefix='/api')  # This will handle /api/login and /api/register
    app.register_blueprint(model_bp, url_prefix='/api')  # This will properly handle /api/models
    
    # Serve frontend at root route
    @app.route('/')
    def index():
        return render_template('index.html')
    
    # Add direct routes for login and register pages
    @app.route('/login')
    def login():
        return render_template('login.html')
    
    @app.route('/register')
    def register():
        return render_template('register.html')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        return {"status": "healthy"}, 200
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Not found"}), 404
        
    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500
    
    logger.info("Application initialization complete")
    return app