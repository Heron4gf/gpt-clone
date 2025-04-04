# app/services/chat_service.py
import asyncio
from typing import Dict, List, Any, AsyncGenerator

# Import specific types mentioned in docs if needed elsewhere, maybe not here
# from openai.types.responses import ResponseTextDeltaEvent

# Import necessary components from the agents library
# Ensure correct types for hints if desired
from agents import Agent, Runner, OpenAIChatCompletionsModel, RunResultStreaming, StreamEvent

# REMOVE flask import if not needed elsewhere after change
# from flask import current_app
import logging
import traceback
import json
import queue      # For type hinting the queue parameter
# import threading # Not needed in this file

from app.models.conversation import Conversation
from app.models.message import Message
from app.config.models import get_model_config, DEFAULT_MODEL
from load_client import load_client, isClientLoaded, get_client

# Configure logging
logger = logging.getLogger(__name__)

# --- EXISTING get_agent function (No changes needed from your last version) ---
def get_agent(model_name=DEFAULT_MODEL):
    """Get or create an agent with the shell tool using configuration from models.py"""
    logger.info(f"[SERVICE_AGENT] Creating agent with model: {model_name}")

    # Ensure client is loaded
    if not isClientLoaded():
        logger.info("[SERVICE_AGENT] Client not loaded, loading client...")
        client = load_client()
        logger.info(f"[SERVICE_AGENT] Client loaded: {client is not None}")
    else:
        logger.info("[SERVICE_AGENT] Client already loaded")
        client = get_client() # Get the loaded client

    if not client:
         # Handle case where client loading failed or returned None
         logger.error("[SERVICE_AGENT] Failed to get OpenAI client instance.")
         raise RuntimeError("OpenAI client is not available.")

    # Get model configuration
    model_config = get_model_config(model_name)
    logger.info(f"[SERVICE_AGENT] Got model config: {model_config}")

    # Create a general assistant agent with shell capabilities
    try:
        # Ensure OpenAIChatCompletionsModel is imported if used here
        agent = Agent(
            name="Assistant",
            instructions=model_config["instructions"],
            model=OpenAIChatCompletionsModel(
                model=model_name,
                openai_client=client # Pass the verified client instance
            ),
            # tools=[execute_shell_command] # Keep commented out if not needed
        )
        logger.info(f"[SERVICE_AGENT] Agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"[SERVICE_AGENT] Error creating agent: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# --- EXISTING generate_response_async (non-streaming) function (No changes needed) ---
async def generate_response_async(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> str:
    """Generate a response using the Agents SDK (non-streaming)."""
    logger.info(f"[SERVICE_NONSTREAM] START: conv={conversation_id}, model={model}")
    try:
        # Fetch conversation history
        conversation = Conversation.get_by_id(conversation_id)
        if not conversation:
            logger.error(f"[SERVICE_NONSTREAM] Conversation {conversation_id} not found")
            raise ValueError(f"Conversation {conversation_id} not found")

        logger.info(f"[SERVICE_NONSTREAM] Found conversation with {len(conversation.messages)} messages")

        # Format history for the agent
        message_history = []
        for msg in conversation.messages:
            role = "assistant" if msg.role == "assistant" else "user"
            message_history.append({"role": role, "content": msg.content})
        message_history.append({"role": "user", "content": user_message})
        logger.info(f"[SERVICE_NONSTREAM] Prepared history with {len(message_history)} messages")

        # Get the agent
        logger.info(f"[SERVICE_NONSTREAM] Getting agent for model: {model}")
        agent = get_agent(model)

        # Run the agent
        logger.info(f"[SERVICE_NONSTREAM] Running agent with history via 'input'")
        # Ensure 'input' is correct argument for non-streaming history if needed
        result = await Runner.run(
            agent,
            input=message_history
        )

        # Extract and return the final output
        final_output = result.final_output if hasattr(result, 'final_output') else str(result)
        logger.info(f"[SERVICE_NONSTREAM] Agent run completed, output length: {len(final_output) if final_output else 0}")
        return final_output

    except Exception as e:
        logger.error(f"[SERVICE_NONSTREAM] Error: {str(e)}")
        logger.error(traceback.format_exc())
        # Return error message string
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
    finally:
        logger.info(f"[SERVICE_NONSTREAM] END: conv={conversation_id}, model={model}")


# --- MODIFIED STREAMING FUNCTION (Accepts app_instance, puts to queue) ---
# Renamed with leading underscore convention for internal use by threaded helper
async def _stream_response_async_to_queue(app_instance, conversation_id: int, user_message: str, model: str, result_queue: queue.Queue): # Added app_instance parameter FIRST
    """
    Generate response using Agents SDK, stream SSE formatted chunks into a queue.
    Handles application context (passed in) for database operations.
    """
    logger.info(f"[SERVICE_STREAM_QUEUE] START: conv={conversation_id}, model={model}")
    full_ai_response = ""
    event_count = 0
    put_chunks_count = 0
    stream_task_completed_normally = False
    # REMOVED: app_instance = current_app._get_current_object() # Cannot get context here

    try:
        # Prepare input
        current_input = user_message
        # IMPORTANT: If get_agent needs app_context, it must be called within a context block here too!
        # This might mean wrapping the agent = get_agent(model) call below in app_instance.app_context()
        # if get_agent relies on current_app internally. For now, assuming it doesn't.
        logger.info(f"[SERVICE_STREAM_QUEUE] Getting agent for model: {model}")
        agent = get_agent(model) # Ensure get_agent is defined correctly above

        # Use Runner.run_streamed()
        logger.info(f"[SERVICE_STREAM_QUEUE] Calling Runner.run_streamed...")
        # Add history here if needed by your agent: chat_history=[...]
        stream_result: RunResultStreaming = Runner.run_streamed(
            agent,
            input=current_input
        )
        logger.info(f"[SERVICE_STREAM_QUEUE] Runner.run_streamed returned type: {type(stream_result)}")

        # Iterate through the stream events
        logger.info(f"[SERVICE_STREAM_QUEUE] Iterating stream events...")
        async for event in stream_result.stream_events():
            event_count += 1
            # (Keep detailed logging from previous version if desired)
            logger.debug(f"[SERVICE_STREAM_QUEUE] Event #{event_count}: Type={event.type}")

            sse_data_payload = None
            delta_content = None

            # --- Corrected Extraction Logic ---
            if event.type == "raw_response_event" and hasattr(event, 'data'):
                if hasattr(event.data, 'delta'):
                    delta_content = event.data.delta
                    if delta_content:
                         delta_content = str(delta_content)
                         put_chunks_count += 1
                         full_ai_response += delta_content
                         sse_data_payload = {"chunk": delta_content}

            # Put data into queue only if we extracted a chunk
            if sse_data_payload:
                sse_string = f"data: {json.dumps(sse_data_payload)}\n\n"
                logger.debug(f"[SERVICE_STREAM_QUEUE] Putting chunk #{put_chunks_count} into queue.")
                result_queue.put(sse_string)
            # else: logger.debug(f"[SERVICE_STREAM_QUEUE] No SSE payload generated for event type {event.type}")

        # If the loop completes without errors
        stream_task_completed_normally = True
        logger.info(f"[SERVICE_STREAM_QUEUE] Finished iterating events normally. Total: {event_count}, Put Chunks: {put_chunks_count}.")

    except Exception as e:
        logger.error(f"[SERVICE_STREAM_QUEUE] Error during agent run/streaming: {str(e)}")
        logger.error(traceback.format_exc())
        # Format and put error SSE string into the queue
        error_msg = f"Error generating streaming response: {str(e)}"
        error_sse = f'data: {json.dumps({"error": error_msg})}\n\n'
        result_queue.put(error_sse)

    finally:
        logger.info(f"[SERVICE_STREAM_QUEUE] Finally block. Full response length: {len(full_ai_response)}")
        # Save the accumulated AI response *only if* the stream completed normally and we got content
        if stream_task_completed_normally and full_ai_response:
             # --- Use the passed app_instance to create context ---
             with app_instance.app_context():
                  logger.info(f"[SERVICE_STREAM_QUEUE] App context pushed for DB save.")
                  try:
                      logger.info(f"[SERVICE_STREAM_QUEUE] Saving full AI response ({len(full_ai_response)} chars) to DB...")
                      # Ensure Message.create is defined and works within context
                      ai_message = Message.create(conversation_id, 'assistant', full_ai_response)
                      if not ai_message: raise Exception("AI Message creation returned None")
                      logger.info(f"[SERVICE_STREAM_QUEUE] Full AI response saved: id={ai_message.id}")
                  except Exception as db_save_err:
                      logger.error(f"[SERVICE_STREAM_QUEUE] Failed to save full AI response (within context): {db_save_err}", exc_info=True)
                      # Put DB save error into queue AFTER trying to save
                      err_save_sse = f'data: {json.dumps({"error": f"Failed to save full response: {db_save_err!s}"})}\n\n'
                      result_queue.put(err_save_sse)
             # --- Context is automatically popped when 'with' block exits ---
             logger.info(f"[SERVICE_STREAM_QUEUE] App context popped after DB save attempt.")
        elif stream_task_completed_normally:
             logger.warning("[SERVICE_STREAM_QUEUE] Stream completed normally but no AI response content generated/accumulated.")
        else:
             logger.warning("[SERVICE_STREAM_QUEUE] Stream did not complete normally, skipping DB save.")

        # Signal the end of generation by putting None in the queue
        logger.info("[SERVICE_STREAM_QUEUE] Putting None sentinel into queue.")
        result_queue.put(None)
        logger.info("[SERVICE_STREAM_QUEUE] END")


# --- EXISTING generate_response (sync wrapper for non-streaming) function (No changes needed) ---
def generate_response(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> str:
    """Synchronous wrapper for the async non-streaming response generator."""
    logger.info(f"[SERVICE_SYNC_WRAP] START: conv={conversation_id}, model={model}")
    try:
        # Uses asyncio.run to call the non-streaming async function
        response = asyncio.run(generate_response_async(conversation_id, user_message, model))
        logger.info(f"[SERVICE_SYNC_WRAP] Response received, length: {len(response) if response else 0}")
        return response
    except Exception as e:
        logger.error(f"[SERVICE_SYNC_WRAP] Error: {str(e)}")
        logger.error(traceback.format_exc())
        # Returns error message string
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}"
    finally:
        logger.info(f"[SERVICE_SYNC_WRAP] END: conv={conversation_id}, model={model}")