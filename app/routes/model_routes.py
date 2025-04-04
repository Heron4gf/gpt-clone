# app/routes/model_routes.py
from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required
from app.config.models import get_available_models

model_bp = Blueprint('model', __name__)

@model_bp.route('/models', methods=['GET'])
@jwt_required()
def get_models():
    """Get a list of all available models."""
    models = get_available_models()
    return jsonify({
        "models": [{"id": model_id, "display_name": display_name} for model_id, display_name in models]
    }), 200
