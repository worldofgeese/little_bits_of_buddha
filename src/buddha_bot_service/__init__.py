"""
Buddha Bot Service - A simplified single-service Telegram bot that speaks as the Buddha.

This module provides a single FastAPI service that:
1. Receives Telegram messages via webhooks
2. Calls OpenAI API with a Buddha persona
3. Sends responses back to Telegram

Architecture:
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Telegram API  │────►│   FastAPI App   │────►│    OpenAI API   │
│   (webhooks)    │     │   (this app)    │     │    (GPT model)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import os
import logging
from typing import Optional
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Little Bits of Buddha",
    description="A Telegram bot that speaks as the Buddha",
    version="2.0.0"
)

# Initialize OpenAI client
openai_client: Optional[OpenAI] = None

# Buddha system prompt - defines the persona
BUDDHA_SYSTEM_PROMPT = """You are the Buddha. You teach only the Dhamma, only what is fundamental 
to the holy life as you profess in the Simsapa Sutta. You speak in the style of the Tathagata, 
the Buddha, the Awakened One of the Early Buddhist Canon. You are compassionate, wise, and 
patient. You speak in short, memorable teachings. You never break character."""


# ============================================================================
# Function: get_buddha_system_prompt
# ============================================================================
def get_buddha_system_prompt() -> str:
    """
    Returns the system prompt that defines the Buddha persona.
    
    Returns:
        str: The Buddha persona system prompt
    """
    return BUDDHA_SYSTEM_PROMPT


# ============================================================================
# Function: should_respond_to_message
# ============================================================================
def should_respond_to_message(update: dict) -> bool:
    """
    Determines if the bot should respond to a given Telegram update.
    
    Args:
        update: A dictionary containing a Telegram update
        
    Returns:
        bool: True if the update contains a text message, False otherwise
    """
    if not isinstance(update, dict):
        return False
    
    message = update.get("message", {})
    
    if not isinstance(message, dict):
        return False
    
    # Check if message contains text
    return "text" in message


# ============================================================================
# Function: extract_chat_id
# ============================================================================
def extract_chat_id(update: dict) -> Optional[int]:
    """
    Extracts the chat ID from a Telegram update.
    
    Args:
        update: A dictionary containing a Telegram update
        
    Returns:
        Optional[int]: The chat ID, or None if not found
    """
    if not isinstance(update, dict):
        return None
    
    message = update.get("message", {})
    
    if not isinstance(message, dict):
        return None
    
    chat = message.get("chat", {})
    
    if not isinstance(chat, dict):
        return None
    
    return chat.get("id")


# ============================================================================
# Function: extract_message_text
# ============================================================================
def extract_message_text(update: dict) -> Optional[str]:
    """
    Extracts the message text from a Telegram update.
    
    Args:
        update: A dictionary containing a Telegram update
        
    Returns:
        Optional[str]: The message text, or None if not found
    """
    if not isinstance(update, dict):
        return None
    
    message = update.get("message", {})
    
    if not isinstance(message, dict):
        return None
    
    return message.get("text")


# ============================================================================
# Function: build_telegram_response
# ============================================================================
def build_telegram_response(chat_id: int, text: str) -> dict:
    """
    Builds a response payload for the Telegram sendMessage API.
    
    Args:
        chat_id: The Telegram chat ID to send the message to
        text: The text message to send
        
    Returns:
        dict: A dictionary suitable for the Telegram API
    """
    return {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }


# ============================================================================
# Class: OpenAIClient
# ============================================================================
class OpenAIClient:
    """
    A wrapper around the OpenAI client for getting Buddha responses.
    
    Attributes:
        client: The underlying OpenAI client
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initializes the OpenAI client.
        
        Args:
            api_key: The OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
        
        if not api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized")
    
    def get_buddha_response(self, user_message: str) -> str:
        """
        Gets a response from OpenAI with the Buddha persona.
        
        Args:
            user_message: The user's message to respond to
            
        Returns:
            str: The Buddha's response
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",  # Using the latest efficient model
                messages=[
                    {"role": "system", "content": get_buddha_system_prompt()},
                    {"role": "user", "content": user_message}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            bot_response = response.choices[0].message.content
            logger.info(f"Buddha response: {bot_response[:100]}...")
            return bot_response
        
        except Exception as e:
            logger.error(f"Error getting Buddha response: {e}")
            return "I am unable to respond at this moment. May you find peace."


# ============================================================================
# Helper Functions
# ============================================================================
def get_openai_client() -> OpenAIClient:
    """
    Gets or creates the OpenAI client singleton.
    
    Returns:
        OpenAIClient: The OpenAI client instance
    """
    global openai_client
    
    if openai_client is None:
        openai_client = OpenAIClient()
    
    return openai_client


def get_telegram_bot_token() -> str:
    """
    Gets the Telegram bot token from environment.
    
    Returns:
        str: The Telegram bot token
        
    Raises:
        ValueError: If the token is not set
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    if not token:
        raise ValueError("Telegram bot token is required. Set TELEGRAM_BOT_TOKEN environment variable.")
    
    return token


# ============================================================================
# API Endpoints
# ============================================================================
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint with service info."""
    return {
        "service": "Little Bits of Buddha",
        "version": "2.0.0",
        "status": "running"
    }


@app.post("/webhook")
async def telegram_webhook(request: Request):
    """
    Handles incoming Telegram webhook updates.
    
    This endpoint receives messages from Telegram, processes them
    through the Buddha persona, and sends responses back.
    """
    try:
        # Parse the update
        update = await request.json()
        
        # Log the update
        logger.info(f"Received update: {update.get('update_id', 'unknown')}")
        
        # Check if we should respond
        if not should_respond_to_message(update):
            logger.info("Ignoring update (not a text message)")
            return {"status": "ignored"}
        
        # Extract message details
        chat_id = extract_chat_id(update)
        user_message = extract_message_text(update)
        
        if chat_id is None or user_message is None:
            logger.warning("Could not extract chat_id or message text")
            return {"status": "error", "reason": "missing_fields"}
        
        logger.info(f"Processing message from chat {chat_id}: {user_message[:50]}...")
        
        # Get Buddha's response
        ai_client = get_openai_client()
        bot_response = ai_client.get_buddha_response(user_message)
        
        # Build and return response
        response = build_telegram_response(chat_id, bot_response)
        
        logger.info(f"Sending response to chat {chat_id}")
        
        # Send response to Telegram
        telegram_token = get_telegram_bot_token()
        telegram_url = f"https://api.telegram.org/bot{telegram_token}/sendMessage"
        
        import httpx
        async with httpx.AsyncClient() as client:
            resp = await client.post(telegram_url, json=response)
            resp.raise_for_status()
        
        return {"status": "ok", "response_sent": True}
    
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# Main Entry Point
# ============================================================================
if __name__ == "__main__":
    import uvicorn
    
    # Get configuration
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 8080))
    
    logger.info(f"Starting Buddha Bot Service on {host}:{port}")
    
    uvicorn.run(
        "buddha_bot_service:app",
        host=host,
        port=port,
        reload=False
    )
