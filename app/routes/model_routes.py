# app/routes/model_routes.py
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, verify_jwt_in_request, get_jwt_identity
from app.config.models import get_available_models

model_bp = Blueprint('model', __name__)

@model_bp.route('/models', methods=['GET'])
def get_models():
    """Get a list of all available models."""
    # Try to verify JWT but don't require it
    try:
        verify_jwt_in_request()
    except:
        # If no valid JWT, still return models
        pass
    
    models = get_available_models()
    return jsonify({
        "models": [{"id": model_id, "display_name": display_name} for model_id, display_name in models]
    }), 200