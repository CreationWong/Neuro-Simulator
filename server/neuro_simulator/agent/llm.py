# agent/llm.py
"""
LLM client for the Neuro Simulator Agent
"""

from typing import Optional
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from google import genai
from google.genai import types
from openai import AsyncOpenAI
from ..config import config_manager

class LLMClient:
    """A completely independent LLM client for the built-in agent."""
    
    def __init__(self):
        self.client = None
        self.model_name = None
        self._initialize_client()
        
    def _initialize_client(self):
        """Initializes the LLM client based on the 'agent' section of the config."""
        settings = config_manager.settings
        provider = settings.agent.agent_provider.lower()
        
        if provider == "gemini":
            api_key = settings.api_keys.gemini_api_key
            if not api_key:
                raise ValueError("GEMINI_API_KEY is not set in configuration for the agent.")
            
            # Use the new client-based API as per the latest documentation
            self.client = genai.Client(api_key=api_key)
            self.model_name = settings.agent.agent_model
            self._generate_func = self._generate_gemini
            
        elif provider == "openai":
            api_key = settings.api_keys.openai_api_key
            if not api_key:
                raise ValueError("OPENAI_API_KEY is not set in configuration for the agent.")
            
            self.model_name = settings.agent.agent_model
            self.client = AsyncOpenAI(
                api_key=api_key, 
                base_url=settings.api_keys.openai_api_base_url
            )
            self._generate_func = self._generate_openai
        else:
            raise ValueError(f"Unsupported agent provider in config: {settings.agent.agent_provider}")
            
        print(f"Agent LLM client initialized. Provider: {provider.upper()}, Model: {self.model_name}")

    async def _generate_gemini(self, prompt: str, max_tokens: int) -> str:
        """Generates text using the Gemini model with the new SDK."""
        import asyncio
        
        generation_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            # temperature can be added later if needed from config
        )
        
        try:
            # The new client's generate_content is synchronous, run it in a thread
            response = await asyncio.to_thread(
                self.client.models.generate_content,
                model=self.model_name,
                contents=prompt,
                config=generation_config
            )
            return response.text if response and response.text else ""
        except Exception as e:
            print(f"Error in _generate_gemini: {e}")
            return ""

    async def _generate_openai(self, prompt: str, max_tokens: int) -> str:
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                # temperature can be added to config if needed
            )
            if response.choices and response.choices[0].message and response.choices[0].message.content:
                return response.choices[0].message.content.strip()
            return ""
        except Exception as e:
            print(f"Error in _generate_openai: {e}")
            return ""
        
    async def generate(self, prompt: str, max_tokens: int = 1000) -> str:
        """Generate text using the configured LLM."""
        if not self.client:
            raise RuntimeError("LLM Client is not initialized.")
        try:
            result = await self._generate_func(prompt, max_tokens)
            # Ensure we always return a string, even if the result is None
            return result if result is not None else ""
        except Exception as e:
            print(f"Error generating text with Agent LLM: {e}")
            return "My brain is not working, tell Vedal to check the logs."