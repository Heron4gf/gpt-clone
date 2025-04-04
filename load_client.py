from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
import logging
from agents import set_default_openai_client, set_tracing_disabled

logger = logging.getLogger(__name__)
client = None

def get_client():
    global client
    return client

def isClientLoaded():
    global client
    return client is not None

def load_client():
    logger.info("[DEBUG] Loading OpenAI client")
    try:
        load_dotenv()
        
        # Check for required environment variables
        api_key = os.getenv("OPENROUTER_API_KEY")
        helicone_key = os.getenv("HELICONE_API_KEY")
        
        if not api_key:
            logger.error("[DEBUG] OPENROUTER_API_KEY not found in environment variables")
            raise ValueError("OPENROUTER_API_KEY is required but not found in environment variables")
            
        if not helicone_key:
            logger.error("[DEBUG] HELICONE_API_KEY not found in environment variables")
            raise ValueError("HELICONE_API_KEY is required but not found in environment variables")
        
        logger.info("[DEBUG] Creating AsyncOpenAI client")
        global client
        client = AsyncOpenAI(
            base_url="https://gateway.helicone.ai/api/v1",
            api_key=api_key,
            default_headers={
                "Helicone-Auth": f"Bearer {helicone_key}",
                "Helicone-Target-Url": "https://openrouter.ai",
                "Helicone-Target-Provider": "OpenRouter",
                "Helicone-Cache-Enabled": "true",
                "Cache-Control": "max-age=3600",
                "Helicone-LLM-Security-Enabled": "true"
            }
        )
        
        logger.info("[DEBUG] Configuring agents SDK")
        set_tracing_disabled(True)
        set_default_openai_client(client)
        logger.info("[DEBUG] Client loaded successfully")
        return client
        
    except Exception as e:
        logger.error(f"[DEBUG] Error loading client: {str(e)}", exc_info=True)
        raise