# app/routes/admin_routes.py
from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
import os

from app.models.user import User
from app.models.registration_key import RegistrationKey
from app.utils.key_management import load_keys_from_file

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/keys', methods=['GET'])
@jwt_required()
def admin_keys():
    """Admin page to manage registration keys."""
    # Check if the user is admin (user id 1 for simplicity)
    user_id = get_jwt_identity()
    if user_id != 1:
        return jsonify({"error": "Unauthorized"}), 403
    
    keys = RegistrationKey.get_all()
    return render_template('admin/keys.html', keys=keys)

@admin_bp.route('/api/admin/keys/generate', methods=['POST'])
@jwt_required()
def api_generate_key():
    """Generate a new registration key."""
    user_id = get_jwt_identity()
    if user_id != 1:
        return jsonify({"error": "Unauthorized"}), 403
    
    key = RegistrationKey.create()
    return jsonify({
        "message": "Key generated successfully",
        "key": key.to_dict()
    }), 201

@admin_bp.route('/api/admin/keys/load', methods=['POST'])
@jwt_required()
def api_load_keys():
    """Load keys from the keys.txt file."""
    user_id = get_jwt_identity()
    if user_id != 1:
        return jsonify({"error": "Unauthorized"}), 403
    
    success, message = load_keys_from_file()
    
    if success:
        return jsonify({"message": message}), 200
    else:
        return jsonify({"error": message}), 400

@admin_bp.route('/api/admin/keys', methods=['GET'])
@jwt_required()
def api_get_keys():
    """Get all registration keys."""
    user_id = get_jwt_identity()
    if user_id != 1:
        return jsonify({"error": "Unauthorized"}), 403
    
    keys = RegistrationKey.get_all()
    return jsonify({
        "keys": [key.to_dict() for key in keys]
    }), 200
