"""Base agent abstractions for Tech Radar."""

from abc import ABC, abstractmethod
from typing import Any, List


class BaseAgent(ABC):
    """Abstract base class for all Tech Radar agents."""

    @abstractmethod
    def process(self, items: List[Any]) -> List[Any]:
        """Process data input and return annotated output."""
        raise NotImplementedError
