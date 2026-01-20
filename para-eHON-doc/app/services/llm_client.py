"""
LLM Client Service
==================
Wrapper for the Dailoqa LLM SDK.
"""
from typing import Optional
from app.config import settings


class LLMClient:
    """Client for interacting with the LLM API."""
    
    def __init__(self):
        self._chat = None
        self._initialize()
    
    def _initialize(self):
        """Initialize the LLM client."""
        try:
            from dailoqa_sdk.chat_ai import ChatDailoqa
            
            self._chat = ChatDailoqa(
                base_url=settings.LLM_BASE_URL,
                api_key=settings.LLM_API_KEY,
                model=settings.MODEL_NAME
            )
            print(f"✓ LLM Client initialized with model: {settings.MODEL_NAME}")
        except ImportError:
            print("⚠ dailoqa_sdk not found. LLM features will not work.")
            self._chat = None
        except Exception as e:
            print(f"⚠ Failed to initialize LLM client: {e}")
            self._chat = None
    
    def invoke(self, prompt: str) -> str:
        """Send a prompt to the LLM and return the response."""
        if self._chat is None:
            raise RuntimeError("LLM client not initialized")
        
        response = self._chat.invoke(prompt)
        return response.content
    
    @property
    def is_available(self) -> bool:
        """Check if the LLM client is available."""
        return self._chat is not None


# Global instance
llm_client = LLMClient()