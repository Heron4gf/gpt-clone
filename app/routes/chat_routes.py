# app/routes/chat_routes.py
from flask import Blueprint, request, jsonify, Response # Removed stream_with_context, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
import json
import asyncio
import queue      # <-- Import queue
import threading  # <-- Import threading

# Assuming DEFAULT_MODEL is defined correctly in this config path
from app.config.models import DEFAULT_MODEL

from app.models.conversation import Conversation
from app.models.message import Message
# Import the NON-streaming function and the MODIFIED streaming function (now prefixed with _)
from app.services.chat_service import generate_response, _stream_response_async_to_queue # Use the queue version

chat_bp = Blueprint('chat', __name__)
logger = logging.getLogger(__name__)


# --- HELPER TO RUN ASYNC IN THREAD (Should be defined once, e.g., here or in utils.py) ---
def run_async_in_thread(target_async_func, *args):
    """Helper to run an async function within its own event loop in a separate thread."""
    logger.info(f"[HELPER_THREAD] Starting new thread for {target_async_func.__name__}")
    def thread_target():
        # Each thread needs its own event loop when using asyncio this way
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info(f"[HELPER_THREAD] Thread {threading.current_thread().name} started with new event loop.")
        try:
            # Run the passed async function until it completes
            loop.run_until_complete(target_async_func(*args))
            logger.info(f"[HELPER_THREAD] Thread {threading.current_thread().name} async task completed.")
        except Exception as e:
             logger.error(f"[HELPER_THREAD] Exception in thread {threading.current_thread().name}: {e}", exc_info=True)
        finally:
            logger.info(f"[HELPER_THREAD] Thread {threading.current_thread().name} closing event loop.")
            loop.close()
            logger.info(f"[HELPER_THREAD] Thread {threading.current_thread().name} finished.")

    # Create and start the daemon thread
    thread = threading.Thread(target=thread_target, daemon=True)
    thread.start()
    return thread


# --- Keep existing routes (GET /conversations, POST /conversations, GET/PUT/DELETE /conversations/<id>) ---
# (Ensure they use int(user_id_str) for comparisons/DB calls)
@chat_bp.route('/conversations', methods=['GET'])
@jwt_required(optional=True)
def get_conversations():
    user_id_str = get_jwt_identity()
    if user_id_str is None: return jsonify({"error": "Authentication required", "conversations": []}), 401 # Changed to 401
    try:
        user_id_int = int(user_id_str)
        conversations = Conversation.get_by_user_id(user_id_int)
        return jsonify({"conversations": [conv.to_dict() for conv in conversations]}), 200
    except ValueError: logger.error(f"[GET /conversations] Invalid JWT ID: {user_id_str}"); return jsonify({"error": "Invalid ID"}), 401
    except Exception as e: logger.error(f"[GET /conversations] Error: {e}", exc_info=True); return jsonify({"error": "Failed fetch"}), 500

@chat_bp.route('/conversations', methods=['POST'])
@jwt_required()
def create_conversation():
    user_id_str = get_jwt_identity()
    data = request.get_json(); title = data.get('title', 'New Conversation')
    if not user_id_str: return jsonify({"error": "Auth required"}), 401
    try:
        user_id_int = int(user_id_str)
        conversation = Conversation.create(user_id_int, title)
        if not conversation: raise Exception("Conversation creation failed")
        logger.info(f"[POST /conversations] Created: id={conversation.id}, user={user_id_int}")
        return jsonify({"message": "Created", "conversation": conversation.to_dict()}), 201
    except ValueError: logger.error(f"[POST /conversations] Invalid JWT ID: {user_id_str}"); return jsonify({"error": "Invalid ID"}), 401
    except Exception as e: logger.error(f"[POST /conversations] Error: {e}", exc_info=True); return jsonify({"error": "Failed create"}), 500

@chat_bp.route('/conversations/<int:conversation_id>', methods=['GET'])
@jwt_required()
def get_conversation(conversation_id):
    user_id_str = get_jwt_identity()
    conversation = Conversation.get_by_id(conversation_id)
    try:
        user_id_int = int(user_id_str)
        if not conversation or conversation.user_id != user_id_int: logger.warning(f"[GET /conv/{conversation_id}] Unauthorized user {user_id_int}"); return jsonify({"error": "Not found/unauthorized"}), 404
        return jsonify({"conversation": conversation.to_dict()}), 200
    except ValueError: logger.error(f"[GET /conv/{conversation_id}] Invalid JWT ID: {user_id_str}"); return jsonify({"error": "Invalid ID"}), 401
    except Exception as e: logger.error(f"[GET /conv/{conversation_id}] Error: {e}", exc_info=True); return jsonify({"error": "Failed fetch"}), 500

@chat_bp.route('/conversations/<int:conversation_id>', methods=['PUT'])
@jwt_required()
def update_conversation(conversation_id):
    user_id_str = get_jwt_identity()
    data = request.get_json(); title = data.get('title')
    if not title: return jsonify({"error": "Title required"}), 400
    conversation = Conversation.get_by_id(conversation_id)
    try:
        user_id_int = int(user_id_str)
        if not conversation or conversation.user_id != user_id_int: logger.warning(f"[PUT /conv/{conversation_id}] Unauthorized user {user_id_int}"); return jsonify({"error": "Not found/unauthorized"}), 404
        conversation.update_title(title)
        updated_conversation = Conversation.get_by_id(conversation_id)
        logger.info(f"[PUT /conv/{conversation_id}] Updated for user {user_id_int}")
        return jsonify({"message": "Updated", "conversation": updated_conversation.to_dict()}), 200
    except ValueError: logger.error(f"[PUT /conv/{conversation_id}] Invalid JWT ID: {user_id_str}"); return jsonify({"error": "Invalid ID"}), 401
    except Exception as e: logger.error(f"[PUT /conv/{conversation_id}] Error: {e}", exc_info=True); return jsonify({"error": "Failed update"}), 500

@chat_bp.route('/conversations/<int:conversation_id>', methods=['DELETE'])
@jwt_required()
def delete_conversation(conversation_id):
    user_id_str = get_jwt_identity()
    conversation = Conversation.get_by_id(conversation_id)
    try:
        user_id_int = int(user_id_str)
        if not conversation or conversation.user_id != user_id_int: logger.warning(f"[DELETE /conv/{conversation_id}] Unauthorized user {user_id_int}"); return jsonify({"error": "Not found/unauthorized"}), 404
        deleted = conversation.delete()
        if not deleted: raise Exception("Deletion failed in DB")
        logger.info(f"[DELETE /conv/{conversation_id}] Deleted for user {user_id_int}")
        return jsonify({"message": "Deleted"}), 200
    except ValueError: logger.error(f"[DELETE /conv/{conversation_id}] Invalid JWT ID: {user_id_str}"); return jsonify({"error": "Invalid ID"}), 401
    except Exception as e: logger.error(f"[DELETE /conv/{conversation_id}] Error: {e}", exc_info=True); return jsonify({"error": "Failed delete"}), 500

# --- EXISTING NON-STREAMING Message Route (No changes needed) ---
@chat_bp.route('/conversations/<int:conversation_id>/messages', methods=['POST'])
@jwt_required()
def send_message(conversation_id):
    """Handles non-streaming message sending."""
    user_id_str = get_jwt_identity(); data = request.get_json()
    logger.info(f"[POST /messages] Received: user={user_id_str}, conv={conversation_id}, data={data}")
    content = data.get('content'); model = data.get('model', DEFAULT_MODEL)
    if not content: logger.warning("[POST /messages] Content missing"); return jsonify({"error": "Content required"}), 400
    conversation = Conversation.get_by_id(conversation_id)
    try: user_id_int = int(user_id_str)
    except ValueError: logger.error(f"[POST /messages] Invalid JWT ID: {user_id_str}"); return jsonify({"error": "Invalid ID"}), 401
    if not conversation or conversation.user_id != user_id_int: logger.warning(f"[POST /messages] Unauthorized"); return jsonify({"error": "Not found/unauthorized"}), 404
    try: # Save user message
        user_message = Message.create(conversation_id, 'user', content)
        if not user_message: raise Exception("User msg save failed")
        logger.info(f"[POST /messages] User message saved: id={user_message.id}")
    except Exception as db_err: logger.error(f"[POST /messages] DB Error user msg: {db_err}", exc_info=True); return jsonify({"error": "Failed save user message"}), 500
    try: # Call service and save AI message
        ai_content = generate_response(conversation_id, content, model) # Calls sync wrapper
        logger.info(f"[POST /messages] Service response len: {len(ai_content)}")
        ai_message = Message.create(conversation_id, 'assistant', ai_content)
        if not ai_message: raise Exception("AI msg save failed")
        logger.info(f"[POST /messages] Assistant message saved: id={ai_message.id}")
        updated_conversation = Conversation.get_by_id(conversation_id)
        return jsonify({"conversation": updated_conversation.to_dict()}), 200
    except Exception as e: logger.error(f"[POST /messages] Error service/AI save: {e}", exc_info=True); return jsonify({"error": f"Failed generate/save response: {str(e)}"}), 500


# --- MODIFIED STREAMING ROUTE (Using Thread/Queue) ---
@chat_bp.route('/conversations/<int:conversation_id>/stream', methods=['POST'])
@jwt_required()
def stream_message(conversation_id):
    """Handles POST requests to stream chat responses using Thread/Queue."""
    user_id_str = get_jwt_identity()
    data = request.get_json()
    content = data.get('content')
    model = data.get('model', DEFAULT_MODEL)
    logger.info(f"[ROUTE_STREAM_Q] START: user={user_id_str}, conv={conversation_id}, model={model}")

    if not content:
        logger.warning("[ROUTE_STREAM_Q] Content missing")
        return jsonify({"error": "Message content is required"}), 400

    # --- Authorization Check ---
    conversation = Conversation.get_by_id(conversation_id)
    try:
        user_id_int = int(user_id_str)
    except ValueError:
        logger.error(f"[ROUTE_STREAM_Q] Invalid user ID format: {user_id_str}")
        return jsonify({"error": "Invalid user identity"}), 401

    if not conversation or conversation.user_id != user_id_int:
        logger.warning(f"[ROUTE_STREAM_Q] Unauthorized: conv_owner={conversation.user_id if conversation else 'None'}, req_user={user_id_int}")
        return jsonify({"error": "Conversation not found or unauthorized"}), 404
    # --- End Auth Check ---

    # --- Save User Message ---
    logger.info(f"[ROUTE_STREAM_Q] Saving user message...")
    try:
        user_message = Message.create(conversation_id, 'user', content)
        if not user_message: raise Exception("Message creation returned None")
        logger.info(f"[ROUTE_STREAM_Q] User message saved: id={user_message.id}")
    except Exception as db_err:
         logger.error(f"[ROUTE_STREAM_Q] DB Error saving user msg: {db_err}", exc_info=True)
         return jsonify({"error": "Failed to save user message"}), 500
    # --- End Save ---

    # Create the queue for this request to receive SSE formatted strings
    result_queue = queue.Queue()

    # Define the synchronous generator that reads from the queue
    def queue_reader_generator():
        """Synchronous generator yields items received from the queue."""
        logger.info("[ROUTE_STREAM_Q] queue_reader_generator started.")
        items_yielded = 0
        try:
            # Start the async service function in the background thread
            logger.info("[ROUTE_STREAM_Q] Starting background thread for service...")
            # Pass necessary args for the service func + the queue
            run_async_in_thread(
                _stream_response_async_to_queue, # Target async func in service
                conversation_id,                 # Args for target...
                content,
                model,
                result_queue                     # The queue
            )
            logger.info("[ROUTE_STREAM_Q] Background thread started.")

            # Loop, getting items from the queue (blocks)
            while True:
                item = result_queue.get() # Wait for an item from the background thread
                # logger.debug(f"[ROUTE_STREAM_Q] Queue reader got item: {item!r}") # Very verbose

                # Check for the None sentinel to stop
                if item is None:
                    logger.info("[ROUTE_STREAM_Q] Queue reader received None sentinel, stopping.")
                    break # Exit the while loop

                # Yield the item (which is already an SSE formatted string from the service)
                items_yielded += 1
                logger.debug(f"[ROUTE_STREAM_Q] Yielding item #{items_yielded}")
                yield item # This yield goes to the Flask Response

            logger.info(f"[ROUTE_STREAM_Q] queue_reader_generator finished after yielding {items_yielded} items.")
        except Exception as e:
            logger.error(f"[ROUTE_STREAM_Q] Error in queue_reader_generator: {e}", exc_info=True)
            # Attempt to yield an error back
            try:
                 # Ensure error message is also SSE formatted
                 error_payload = json.dumps({"error": f"Error reading stream: {e!s}"})
                 yield f'data: {error_payload}\n\n'
            except: pass # Ignore errors during error yield
        finally:
             logger.info("[ROUTE_STREAM_Q] queue_reader_generator finally block.")
             # No need to mark task done for simple Queue get loop like this

    # Return the Response object, passing the SYNCHRONOUS generator directly
    logger.info("[ROUTE_STREAM_Q] Returning Response with sync queue reader generator.")
    # No stream_with_context needed here as queue_reader_generator is sync
    return Response(queue_reader_generator(), mimetype='text/event-stream')