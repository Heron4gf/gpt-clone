# app/routes/chat_routes.py
from flask import Blueprint, request, jsonify, current_app, Response, stream_with_context
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import json

import asyncio

from app.models.conversation import Conversation
from app.models.message import Message
from app.services.chat_service import generate_response
from ..services.chat_service import stream_response_async

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
    # user_id_str is a string from JWT
    user_id_str = get_jwt_identity()
    data = request.get_json()
    logger.info(f"[DEBUG] Received message request: user_id={user_id_str}, conversation_id={conversation_id}, data={data}")

    content = data.get('content')
    model = data.get('model', 'openai/gpt-4o-mini')

    if not content:
        logger.warning(f"[DEBUG] Message content is missing in request data: {data}")
        return jsonify({"error": "Message content is required"}), 400

    logger.info(f"[DEBUG] Processing message with model: {model}")

    conversation = Conversation.get_by_id(conversation_id)
    logger.info(f"[DEBUG] Retrieved conversation: {conversation}")

    # --- FIX HERE: Convert user_id_str to int for comparison ---
    try:
        user_id_int = int(user_id_str)
    except ValueError:
        # Should not happen if JWT identity is always a numeric string, but good practice
        logger.error(f"[DEBUG] Invalid user ID format in JWT: {user_id_str}")
        return jsonify({"error": "Invalid user identity"}), 401

    # Compare integers: conversation.user_id (int) != user_id_int (int)
    if not conversation or conversation.user_id != user_id_int:
        logger.warning(f"[DEBUG] Conversation not found or unauthorized: conv_owner={conversation.user_id if conversation else 'None'}, request_user_id={user_id_int}")
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    # -------------------------------------------------------------

    logger.info(f"[DEBUG] Creating user message: conversation_id={conversation_id}, content={content[:50]}...")
    user_message = Message.create(conversation_id, 'user', content)
    logger.info(f"[DEBUG] User message created: {user_message}")

    try:
        logger.info(f"[DEBUG] Calling generate_response with model: {model}")
        ai_content = generate_response(conversation_id, content, model)
        logger.info(f"[DEBUG] Response generated, length: {len(ai_content)}")

        logger.info(f"[DEBUG] Creating assistant message")
        ai_message = Message.create(conversation_id, 'assistant', ai_content)
        logger.info(f"[DEBUG] Assistant message created: {ai_message}")

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
    user_id_str = get_jwt_identity()
    data = request.get_json()
    content = data.get('content')
    model = data.get('model', "non so riuscito a trovare il modello")
    logger.info(f"[ROUTE_STREAM] START: user={user_id_str}, conv={conversation_id}, model={model}") # Log route start

    if not content:
        logger.warning("[ROUTE_STREAM] Content missing")
        return jsonify({"error": "Message content is required"}), 400

    # --- Authorization Check (keep as is) ---
    conversation = Conversation.get_by_id(conversation_id)
    try:
        user_id_int = int(user_id_str)
    except ValueError:
        logger.error(f"[ROUTE_STREAM] Invalid user ID format: {user_id_str}")
        return jsonify({"error": "Invalid user identity"}), 401
    if not conversation or conversation.user_id != user_id_int:
        logger.warning(f"[ROUTE_STREAM] Unauthorized: conv_owner={conversation.user_id if conversation else 'None'}, req_user={user_id_int}")
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    # --- End Auth Check ---

    # --- Save User Message (keep as is) ---
    logger.info(f"[ROUTE_STREAM] Saving user message...")
    try:
        Message.create(conversation_id, 'user', content)
        logger.info("[ROUTE_STREAM] User message saved.")
    except Exception as db_err:
         logger.error(f"[ROUTE_STREAM] DB Error saving user msg: {db_err}", exc_info=True)
         return jsonify({"error": "Failed to save user message"}), 500
    # --- End Save ---


    # Define the generator function for the streaming response
    async def generate_sse():
        logger.info("[ROUTE_STREAM] generate_sse started.") # Log generator start
        full_ai_response = ""
        chunk_count = 0 # Add counter
        try:
            logger.info(f"[ROUTE_STREAM] Calling stream_response_async service...")
            async for chunk in stream_response_async(conversation_id, content, model):
                chunk_count += 1 # Increment counter
                logger.info(f"[ROUTE_STREAM] Received chunk #{chunk_count} from service. Type: {type(chunk)}, Len: {len(chunk) if isinstance(chunk, str) else 'N/A'}") # Log received chunk

                # Check for potential JSON error string from service
                error_data = None
                if isinstance(chunk, str) and chunk.startswith('{"error":'):
                    try:
                         error_data = json.loads(chunk)
                    except json.JSONDecodeError:
                         logger.warning(f"[ROUTE_STREAM] Received potential error chunk, but failed to parse as JSON: {chunk!r}")

                if error_data and "error" in error_data:
                     logger.error(f"[ROUTE_STREAM] Relaying error from service: {error_data['error']}")
                     sse_data = json.dumps({"error": error_data['error']}) # Relay parsed error
                elif isinstance(chunk, str):
                     # Accumulate the response only if it's actual content
                     full_ai_response += chunk
                     # Format for Server-Sent Events (SSE)
                     sse_data = json.dumps({"chunk": chunk})
                else:
                    # Skip if not a string or recognized error format
                    logger.warning(f"[ROUTE_STREAM] Skipping non-string/non-error chunk: {chunk!r}")
                    continue

                sse_string = f"data: {sse_data}\n\n"
                logger.debug(f"[ROUTE_STREAM] Yielding SSE: {sse_string.strip()}") # Log exact SSE string
                yield sse_string
                await asyncio.sleep(0.01) # Keep small sleep

            logger.info(f"[ROUTE_STREAM] Stream finished after {chunk_count} chunks. Full response length: {len(full_ai_response)}")

        except Exception as stream_err:
            logger.error(f"[ROUTE_STREAM] Error during generate_sse iteration: {stream_err}", exc_info=True)
            # Send an error event
            error_data_json = json.dumps({"error": f"Streaming route error: {stream_err}"})
            yield f"data: {error_data_json}\n\n"
        finally:
            # Save the accumulated AI response
            if full_ai_response:
                 try:
                      logger.info(f"[ROUTE_STREAM] Saving full AI response ({len(full_ai_response)} chars) to DB...")
                      Message.create(conversation_id, 'assistant', full_ai_response)
                      logger.info(f"[ROUTE_STREAM] Full AI response saved.")
                 except Exception as db_save_err:
                      logger.error(f"[ROUTE_STREAM] Failed to save full AI response: {db_save_err}", exc_info=True)
            else:
                 logger.warning("[ROUTE_STREAM] No AI response content accumulated to save.")

            # Send a completion marker
            completion_data = json.dumps({"complete": True})
            logger.info("[ROUTE_STREAM] Yielding completion marker.")
            yield f"data: {completion_data}\n\n"
            logger.info("[ROUTE_STREAM] generate_sse finished.")


    # Return the streaming response
    logger.info("[ROUTE_STREAM] Returning Response object.")
    return Response(stream_with_context(generate_sse()), mimetype='text/event-stream')