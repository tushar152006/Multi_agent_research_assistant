from abc import ABC, abstractmethod
from typing import Generic, TypeVar

TInput = TypeVar("TInput")
TOutput = TypeVar("TOutput")


class BaseAgent(ABC, Generic[TInput, TOutput]):
    """Common contract for all specialized agents."""

    name: str

    @abstractmethod
    async def run(self, payload: TInput) -> TOutput:
        """Execute the agent task."""
