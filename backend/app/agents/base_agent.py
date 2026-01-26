from abc import ABC, abstractmethod
from typing import Any, Dict
from ..services.llm_service import llm_service


class BaseAgent(ABC):
    """
    Base class for all agents in the multi-agent system.
    Each agent has a specific role and responsibility.
    """

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.llm = llm_service

    @abstractmethod
    async def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process input and return output.
        Each agent implements its own processing logic.
        """
        pass

    def get_system_prompt(self) -> str:
        """
        Get the system prompt for this agent.
        Override in subclasses for specialized prompts.
        """
        return f"You are {self.name}. {self.description}"
