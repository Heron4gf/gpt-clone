# app/services/chat_service.py
import asyncio
from typing import Dict, List, Any

from agents import Agent, Runner
from flask import current_app
import logging
import traceback

from app.models.conversation import Conversation
from app.models.message import Message
from app.tools.shell_tool import execute_shell_command
from app.config.models import get_model_config, DEFAULT_MODEL
from load_client import load_client, isClientLoaded, get_client

# Configure logging
logger = logging.getLogger(__name__)

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
            tools=[execute_shell_command],
            model=model_name
        )
        logger.info(f"[DEBUG] Agent created successfully")
        return agent
    except Exception as e:
        logger.error(f"[DEBUG] Error creating agent: {str(e)}")
        logger.error(traceback.format_exc())
        raise

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
        
        # Run the agent with the history
        logger.info(f"[DEBUG] Running agent with message history")
        result = await Runner.run(
            agent, 
            input_messages=message_history,
            max_turns=10  # Limit to prevent excessive iterations
        )
        
        # Return the final output
        logger.info(f"[DEBUG] Agent execution completed, result length: {len(result.final_output) if result.final_output else 0}")
        return result.final_output
        
    except Exception as e:
        logger.error(f"[DEBUG] Error in generate_response_async: {str(e)}")
        logger.error(traceback.format_exc())  
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}"

def generate_response(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> str:
    """Synchronous wrapper for the async response generator."""
    logger.info(f"[DEBUG] Starting generate_response with model: {model}")
    try:
        response = asyncio.run(generate_response_async(conversation_id, user_message, model))
        logger.info(f"[DEBUG] Response generated successfully, length: {len(response) if response else 0}")
        return response
    except Exception as e:
        logger.error(f"[DEBUG] Error in generate_response: {str(e)}")
        logger.error(traceback.format_exc())
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}"