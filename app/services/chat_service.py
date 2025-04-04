# app/services/chat_service.py
import asyncio
from typing import Dict, List, Any, AsyncGenerator # Added AsyncGenerator

# Import specific types mentioned in docs
from openai.types.responses import ResponseTextDeltaEvent

# Import necessary components from the agents library
from agents import Agent, Runner, OpenAIChatCompletionsModel, RunResultStreaming, StreamEvent # Added RunResultStreaming, StreamEvent

from flask import current_app
import logging
import traceback
import json # Added json for error formatting

from app.models.conversation import Conversation
from app.models.message import Message
from app.tools.shell_tool import execute_shell_command
from app.config.models import get_model_config, DEFAULT_MODEL
from load_client import load_client, isClientLoaded, get_client

# Configure logging
logger = logging.getLogger(__name__)

# --- EXISTING get_agent function ---
def get_agent(model_name=DEFAULT_MODEL):
    """Get or create an agent with the shell tool using configuration from models.py"""
    logger.info(f"[DEBUG] Creating agent with model: {model_name}")

    if not isClientLoaded():
        logger.info("[DEBUG] Client not loaded, loading client...")
        client = load_client()
        logger.info(f"[DEBUG] Client loaded: {client is not None}")
    else:
        logger.info("[DEBUG] Client already loaded")

    # Get model configuration
    model_config = get_model_config(model_name)
    logger.info(f"[DEBUG] Got model config: {model_config}")

    # Create a general assistant agent with shell capabilities
    try:
        agent = Agent(
            name="ChatGPT Assistant",
            instructions=model_config["instructions"],
            model=OpenAIChatCompletionsModel(
                model=model_name,
                openai_client=get_client() # Ensure get_client() returns AsyncOpenAI client
            ),
            # tools=[execute_shell_command] # Tools are commented out as per user provided code
        )
        logger.info(f"[DEBUG] Agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"[DEBUG] Error creating agent: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# --- EXISTING generate_response_async (non-streaming) function ---
async def generate_response_async(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> str:
    """Generate a response using the Agents SDK."""
    logger.info(f"[DEBUG] Starting generate_response_async with model: {model}")
    try:
        # Fetch conversation history
        conversation = Conversation.get_by_id(conversation_id)
        if not conversation:
            logger.error(f"[DEBUG] Conversation {conversation_id} not found")
            raise ValueError(f"Conversation {conversation_id} not found")

        logger.info(f"[DEBUG] Found conversation with {len(conversation.messages)} messages")

        # Format history for the agent
        # NOTE: Runner.run might need history passed differently than just in 'input'
        message_history = []
        for msg in conversation.messages:
            role = "assistant" if msg.role == "assistant" else "user"
            message_history.append({"role": role, "content": msg.content})

        # Add the new user message to history
        message_history.append({"role": "user", "content": user_message})
        logger.info(f"[DEBUG] Prepared message history with {len(message_history)} messages")

        # Get the agent with specified model
        logger.info(f"[DEBUG] Getting agent for model: {model}")
        agent = get_agent(model)

        # Run the agent with the history passed to 'input'
        # Verify if 'input' is the correct way to pass history for Runner.run
        logger.info(f"[DEBUG] Running agent with message history via 'input'")
        result = await Runner.run(
            agent,
            input=message_history
        )

        # Return the final output
        # Assuming result has final_output attribute based on previous success
        final_output = result.final_output if hasattr(result, 'final_output') else str(result)
        logger.info(f"[DEBUG] Agent execution completed, result length: {len(final_output) if final_output else 0}")
        return final_output

    except Exception as e:
        logger.error(f"[DEBUG] Error in generate_response_async: {str(e)}")
        logger.error(traceback.format_exc())
        # Return error message string
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}"


# --- NEW stream_response_async function ---
async def stream_response_async(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> AsyncGenerator[str, None]:
    """Generate a response using the Agents SDK and stream text chunks based on docs."""
    logger.info(f"[SERVICE_STREAM] START: conv={conversation_id}, model={model}") # Log service start
    try:
        # ... (fetch conversation, prepare input - keep as is) ...
        conversation = Conversation.get_by_id(conversation_id)
        if not conversation: # Basic checks
            logger.error(f"[SERVICE_STREAM] Conversation {conversation_id} not found")
            raise ValueError(f"Conversation {conversation_id} not found")
        current_input = user_message
        agent = get_agent(model)
        # ...

        # Use Runner.run_streamed()
        logger.info(f"[SERVICE_STREAM] Calling Runner.run_streamed...")
        stream_result: RunResultStreaming = Runner.run_streamed(
            agent,
            input=current_input
        )
        logger.info(f"[SERVICE_STREAM] Runner.run_streamed returned: {type(stream_result)}") # Log return type

        # Iterate through the stream events
        event_count = 0
        yielded_chunks_count = 0
        logger.info(f"[SERVICE_STREAM] Iterating through response stream events...")
        async for event in stream_result.stream_events():
            event_count += 1
            logger.debug(f"[SERVICE_STREAM] Received event #{event_count}. Type: {event.type}, Data Type: {type(event.data)}") # Log every event

            # Check for raw text delta events
            if event.type == "raw_response_event" and isinstance(event.data, ResponseTextDeltaEvent):
                delta_content = event.data.delta
                if delta_content: # Ensure there's content in the delta
                    yielded_chunks_count += 1
                    logger.debug(f"[SERVICE_STREAM] Yielding text chunk #{yielded_chunks_count}: '{delta_content}'") # Log yielded chunk
                    yield delta_content # Yield the actual text chunk
            # Optionally log other significant events if needed for debugging
            # elif event.type == "run_item_stream_event" and event.item.type == "message_output_item":
            #     logger.info("[SERVICE_STREAM] Received full message output item event.")

        logger.info(f"[SERVICE_STREAM] Finished iterating stream events. Total events: {event_count}, Yielded text chunks: {yielded_chunks_count}.")

    except Exception as e:
        logger.error(f"[SERVICE_STREAM] Error during stream_response_async: {str(e)}")
        logger.error(traceback.format_exc())
        # Yield a final error message chunk, formatted as JSON
        error_msg = f"Error generating streaming response: {str(e)}"
        try:
            yield json.dumps({"error": error_msg})
        except TypeError:
             yield f'{{"error": "Error generating streaming response: {str(e)}"}}'
    finally:
        logger.info(f"[SERVICE_STREAM] END")

# --- EXISTING generate_response (sync wrapper for non-streaming) function ---
def generate_response(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> str:
    """Synchronous wrapper for the async response generator."""
    logger.info(f"[DEBUG] Starting generate_response with model: {model}")
    try:
        # Uses asyncio.run to call the non-streaming async function
        response = asyncio.run(generate_response_async(conversation_id, user_message, model))
        logger.info(f"[DEBUG] Response generated successfully, length: {len(response) if response else 0}")
        return response
    except Exception as e:
        logger.error(f"[DEBUG] Error in generate_response: {str(e)}")
        logger.error(traceback.format_exc())
        # Returns error message string
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}"