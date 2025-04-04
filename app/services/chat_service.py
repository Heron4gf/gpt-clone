# app/services/chat_service.py
import asyncio
from typing import Dict, List, Any

from agents import Agent, Runner
from flask import current_app
import logging

from app.models.conversation import Conversation
from app.models.message import Message
from app.tools.shell_tool import execute_shell_command
from app.config.models import get_model_config, DEFAULT_MODEL
from load_client import load_client, isClientLoaded, get_client

# Configure logging
logger = logging.getLogger(__name__)

def get_agent(model_name=DEFAULT_MODEL):
    """Get or create an agent with the shell tool using configuration from models.py"""
    if not isClientLoaded():
        load_client()
    
    # Get model configuration
    model_config = get_model_config(model_name)
    
    # Create a general assistant agent with shell capabilities
    agent = Agent(
        name="ChatGPT Assistant",
        instructions=model_config["instructions"],
        tools=[execute_shell_command],
        model=model_name
    )
    return agent

async def generate_response_async(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> str:
    """Generate a response using the Agents SDK."""
    try:
        # Fetch conversation history
        conversation = Conversation.get_by_id(conversation_id)
        if not conversation:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        # Format history for the agent
        message_history = []
        for msg in conversation.messages:
            role = "assistant" if msg.role == "assistant" else "user"
            message_history.append({"role": role, "content": msg.content})
            
        # Add the new user message to history
        message_history.append({"role": "user", "content": user_message})
        
        # Get the agent with specified model
        agent = get_agent(model)
        
        # Run the agent with the history
        result = await Runner.run(
            agent, 
            input_messages=message_history,
            max_turns=10  # Limit to prevent excessive iterations
        )
        
        # Return the final output
        return result.final_output
        
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}", exc_info=True)
        return f"I'm sorry, I encountered an error while processing your request: {str(e)}"

def generate_response(conversation_id: int, user_message: str, model=DEFAULT_MODEL) -> str:
    """Synchronous wrapper for the async response generator."""
    return asyncio.run(generate_response_async(conversation_id, user_message, model))
