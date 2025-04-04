# app/routes/api_routes.py
from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from app.models.user import User
from app.models.registration_key import RegistrationKey

api_bp = Blueprint('api', __name__)

@api_bp.route('/login', methods=['POST'])
def login():
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

@api_bp.route('/register', methods=['POST'])
def register():
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

@api_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """Get information about the currently authenticated user."""
    user_id = get_jwt_identity()
    user = User.get_by_id(user_id)
    
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    return jsonify({
        "user": user.to_dict()
    }), 200