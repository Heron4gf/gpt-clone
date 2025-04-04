# app/config/models.py
"""
Configuration file for AI models and their instructions.
Each model has a specific set of instructions to guide its behavior.
"""

MODELS = {
    "openai/gpt-4o-mini": {
        "display_name": "GPT-4o Mini",
        "instructions": """You are a helpful, friendly AI assistant powered by GPT-4o Mini.
        Answer questions accurately and concisely based on the information provided.
        When you don't know something, admit it instead of making up information.
        You can use the shell tool for computations, data processing, or retrieving information
        when appropriate."""
    },
    "deepseek/deepseek-v3-base:free": {
        "display_name": "DeepSeek v3",
        "instructions": """You are DeepSeek v3, a helpful AI assistant.
        Provide informative, well-structured responses that are factual and insightful.
        Use the shell tool when necessary for complex calculations or data analysis tasks.
        Always prioritize accuracy and clarity in your explanations."""
    }
}

DEFAULT_MODEL = "openai/gpt-4o-mini"

def get_model_config(model_name):
    """Get configuration for a specified model."""
    if model_name not in MODELS:
        model_name = DEFAULT_MODEL
    return MODELS[model_name]

def get_available_models():
    """Get a list of all available models with their display names."""
    return [(key, model["display_name"]) for key, model in MODELS.items()]
