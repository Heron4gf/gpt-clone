# app/routes/auth_routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
import datetime

from app.models.user import User
from app.models.registration_key import RegistrationKey

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Render the login page."""
    return render_template('login.html')

@auth_bp.route('/register', methods=['GET'])
def register_page():
    """Render the registration page."""
    return render_template('register.html')

@auth_bp.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for user registration."""
    data = request.get_json()
    
    # Validate input
    if not all(k in data for k in ['username', 'password', 'registration_key']):
        return jsonify({"error": "Missing required fields"}), 400
    
    # Check if user already exists
    if User.get_by_username(data['username']):
        return jsonify({"error": "Username already exists"}), 409
    
    # Check if the registration key is valid
    reg_key = RegistrationKey.get_by_value(data['registration_key'])
    if not reg_key:
        return jsonify({"error": "Invalid registration key"}), 400
    
    if reg_key.is_used:
        return jsonify({"error": "Registration key has already been used"}), 400
    
    # Create new user
    user = User.create(data['username'], data['password'])
    
    if not user:
        return jsonify({"error": "Failed to create user"}), 500
    
    # Mark the registration key as used
    reg_key.mark_as_used(user.id)
    
    # Generate tokens
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "message": "User registered successfully",
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 201

@auth_bp.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for user login."""
    data = request.get_json()
    
    if not all(k in data for k in ['username', 'password']):
        return jsonify({"error": "Missing username or password"}), 400
    
    user = User.get_by_username(data['username'])
    
    if not user or not user.verify_password(data['password']):
        return jsonify({"error": "Invalid username or password"}), 401
    
    access_token = create_access_token(identity=user.id)
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        "message": "Login successful",
        "user": user.to_dict(),
        "access_token": access_token,
        "refresh_token": refresh_token
    }), 200

@auth_bp.route('/api/refresh', methods=['POST'])
@jwt_required(refresh=True)
def api_refresh():
    """Refresh the access token."""
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    
    return jsonify({
        "access_token": access_token
    }), 200

@auth_bp.route('/api/me', methods=['GET'])
@jwt_required()
def api_get_current_user():
    """Get the current user's information."""
    user_id = get_jwt_identity()
    user = User.get_by_id(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({"user": user.to_dict()}), 200
