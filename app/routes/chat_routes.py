# app/routes/chat_routes.py
from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import json

from app.models.conversation import Conversation
from app.models.message import Message
from app.services.chat_service import generate_response

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)

@chat_bp.route('/conversations', methods=['GET'])
@jwt_required(optional=True)
def get_conversations():
    user_id = get_jwt_identity()
    
    if user_id is None:
        return jsonify({"error": "Authentication required", "conversations": []}), 200
        
    conversations = Conversation.get_by_user_id(user_id)
    
    return jsonify({
        "conversations": [conv.to_dict() for conv in conversations]
    }), 200

@chat_bp.route('/conversations', methods=['POST'])
@jwt_required(optional=True)
def create_conversation():
    user_id = get_jwt_identity()
    
    if user_id is None:
        return jsonify({"error": "Authentication required"}), 401
        
    data = request.get_json()
    title = data.get('title', 'New Conversation')
    
    conversation = Conversation.create(user_id, title)
    
    return jsonify({
        "message": "Conversation created successfully",
        "conversation": conversation.to_dict()
    }), 201

@chat_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    user_id = get_jwt_identity()
    conversation = Conversation.get_by_id(conversation_id)
    
    if not conversation or conversation.user_id != user_id:
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    
    return jsonify({
        "conversation": conversation.to_dict()
    }), 200

@chat_bp.route('/conversations/<int:conversation_id>', methods=['PUT'])
@jwt_required()
def update_conversation(conversation_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    title = data.get('title')
    
    conversation = Conversation.get_by_id(conversation_id)
    
    if not conversation or conversation.user_id != user_id:
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    
    if title:
        conversation.update_title(title)
    
    return jsonify({
        "message": "Conversation updated successfully",
        "conversation": conversation.to_dict()
    }), 200

@chat_bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    user_id = get_jwt_identity()
    conversation = Conversation.get_by_id(conversation_id)
    
    if not conversation or conversation.user_id != user_id:
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    
    conversation.delete()
    
    return jsonify({
        "message": "Conversation deleted successfully"
    }), 200

@chat_bp.route('/conversations/<int:conversation_id>/messages', methods=['POST'])
@jwt_required()
def send_message(conversation_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    logger.info(f"[DEBUG] Received message request: user_id={user_id}, conversation_id={conversation_id}, data={data}")
    
    content = data.get('content')
    model = data.get('model', 'openai/gpt-4o-mini')  # Default to gpt-4o-mini if not specified
    
    if not content:
        logger.warning(f"[DEBUG] Message content is missing in request data: {data}")
        return jsonify({"error": "Message content is required"}), 400
    
    logger.info(f"[DEBUG] Processing message with model: {model}")
    
    conversation = Conversation.get_by_id(conversation_id)
    logger.info(f"[DEBUG] Retrieved conversation: {conversation}")
    
    if not conversation or conversation.user_id != user_id:
        logger.warning(f"[DEBUG] Conversation not found or unauthorized: conv={conversation}, user_id={user_id}")
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    
    # Save user message
    logger.info(f"[DEBUG] Creating user message: conversation_id={conversation_id}, content={content[:50]}...")
    user_message = Message.create(conversation_id, 'user', content)
    logger.info(f"[DEBUG] User message created: {user_message}")
    
    try:
        # Generate response using chat service with specified model
        logger.info(f"[DEBUG] Calling generate_response with model: {model}")
        ai_content = generate_response(conversation_id, content, model)
        logger.info(f"[DEBUG] Response generated, length: {len(ai_content)}")
        
        # Save AI response
        logger.info(f"[DEBUG] Creating assistant message")
        ai_message = Message.create(conversation_id, 'assistant', ai_content)
        logger.info(f"[DEBUG] Assistant message created: {ai_message}")
        
        # Update conversation with updated messages
        updated_conversation = Conversation.get_by_id(conversation_id)
        
        return jsonify({
            "conversation": updated_conversation.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"[DEBUG] Error in send_message: {str(e)}", exc_info=True)
        return jsonify({"error": f"Failed to generate response: {str(e)}"}), 500

@chat_bp.route('/conversations/<int:conversation_id>/stream', methods=['POST'])
@jwt_required()
def stream_message(conversation_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    content = data.get('content')
    
    if not content:
        return jsonify({"error": "Message content is required"}), 400
    
    conversation = Conversation.get_by_id(conversation_id)
    
    if not conversation or conversation.user_id != user_id:
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    
    # Save user message
    user_message = Message.create(conversation_id, 'user', content)
    
    # Define the streaming response
    def generate():
        try:
            # Initialize an empty message to build the response
            complete_response = ""
            
            # Create agent with generator
            # This is a placeholder - actual implementation would depend on how
            # you want to handle streaming with the Agents SDK
            # Replace with actual streaming implementation
            chunks = ["Hello", " there", "! ", "I'm", " responding", " in", " chunks."]
            
            # Stream each chunk
            for chunk in chunks:
                complete_response += chunk
                yield f"data: {json.dumps({'chunk': chunk, 'complete': False})}\n\n"
                
            # Save the complete response after streaming is done
            Message.create(conversation_id, 'assistant', complete_response)
            
            # Send a completion message
            yield f"data: {json.dumps({'chunk': '', 'complete': True, 'full_response': complete_response})}\n\n"
            
        except Exception as e:
            error_msg = f"Error generating streaming response: {str(e)}"
            logger.error(error_msg, exc_info=True)
            yield f"data: {json.dumps({'error': error_msg, 'complete': True})}\n\n"
    
    return Response(stream_with_context(generate()), mimetype='text/event-stream')