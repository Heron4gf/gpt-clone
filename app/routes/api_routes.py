# app/routes/api_routes.py
from flask import Blueprint, request, jsonify, current_app # Ensure current_app is imported
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    jwt_required,
    get_jwt_identity
)
from app.models.user import User
from app.models.registration_key import RegistrationKey

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/login', methods=['POST'])
def login():
    """API endpoint for user login."""
    data = request.get_json()

    # ... (validation checks) ...

    user = User.get_by_username(data['username'])

    # ... (user/password verification) ...

    # --- CHANGE HERE: Convert user.id to string ---
    identity = str(user.id)
    print(f"--- LOGIN CHECK --- Creating token for User ID: {identity} (Type: {type(identity)})") # Verify it's str
    print(f"--- LOGIN CHECK --- Using JWT Secret Key: {current_app.config.get('JWT_SECRET_KEY')}")
    access_token = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)
    print(f"--- LOGIN CHECK --- Generated Access Token starts with: {access_token[:20]}...")
    # ---------------------------------------------

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

    # ... (validation, user/key checks) ...

    user = User.create(data['username'], data['password'])

    # ... (check if user created, mark key used) ...

    # --- CHANGE HERE: Convert user.id to string ---
    identity = str(user.id)
    access_token = create_access_token(identity=identity)
    refresh_token = create_refresh_token(identity=identity)
    # ---------------------------------------------

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
    print(f"--- API_ME CHECK --- Verifying request for endpoint: {request.endpoint}")
    print(f"--- API_ME CHECK --- Using JWT Secret Key: {current_app.config.get('JWT_SECRET_KEY')}")
    print(f"--- API_ME CHECK --- Received Authorization Header: {request.headers.get('Authorization')}")
    try:
        # get_jwt_identity() will now return the ID as a string
        user_id_str = get_jwt_identity()
        print(f"--- API_ME CHECK --- Successfully got identity: {user_id_str} (Type: {type(user_id_str)})")

        # Assuming User.get_by_id can handle a string or you convert it back if needed
        # user = User.get_by_id(int(user_id_str)) # If get_by_id STRICTLY needs int
        user = User.get_by_id(user_id_str) # Try this first, it often works

        if not user:
            # Log this specific case for debugging if it happens
            print(f"--- API_ME CHECK --- User not found for string ID: {user_id_str}")
            return jsonify({"error": "User not found for the provided token"}), 404

        print(f"--- API_ME CHECK --- Found user: {user.username}")
        return jsonify({"user": user.to_dict()}), 200

    except Exception as e:
        print(f"--- API_ME CHECK --- Error during identity processing or user lookup: {e}")
        # Consider more specific error handling based on exception type
        return jsonify({"error": "Error processing token identity or finding user"}), 500


@api_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh the access token using a valid refresh token."""
    # Identity will be string here too from the refresh token
    identity = get_jwt_identity()
    access_token = create_access_token(identity=identity)
    return jsonify(access_token=access_token), 200