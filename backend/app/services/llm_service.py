from typing import Optional, List
from groq import AsyncGroq
from openai import AsyncOpenAI
from ..core.config import settings


class LLMService:
    """
    Service for interacting with LLMs (Groq/LLaMA or OpenAI).
    """

    def __init__(self):
        self.groq_client: Optional[AsyncGroq] = None
        self.openai_client: Optional[AsyncOpenAI] = None

        # Initialize available clients
        if settings.GROQ_API_KEY:
            self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        if settings.OPENAI_API_KEY:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 1024
    ) -> str:
        """
        Generate a response from the LLM.
        Prefers Groq (LLaMA) if available, falls back to OpenAI.
        """
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        # Try Groq first
        if self.groq_client:
            try:
                response = await self.groq_client.chat.completions.create(
                    model=settings.LLM_MODEL,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"Groq error: {e}")

        # Fall back to OpenAI
        if self.openai_client:
            try:
                response = await self.openai_client.chat.completions.create(
                    model="gpt-4-turbo-preview",
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"OpenAI error: {e}")

        raise RuntimeError("No LLM service available. Please configure GROQ_API_KEY or OPENAI_API_KEY.")

    async def generate_json(
            self,
            prompt: str,
            system_prompt: Optional[str] = None,
            temperature: float = 0.3
    ) -> str:
        """
        Generate a JSON response from the LLM.
        Uses lower temperature for more deterministic output.
        """
        json_system = (system_prompt or "") + "\n\nRespond ONLY with valid JSON. No explanations or markdown."
        return await self.generate(prompt, json_system, temperature)


# Singleton instance
llm_service = LLMService()
