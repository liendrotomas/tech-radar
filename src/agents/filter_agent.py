"""
Filter agent.

- Input: list of articles
- Output: only relevant articles
- For now: simple keyword-based filtering (AI, robotics, startup)
"""

from typing import List, Dict
from .base_agent import BaseAgent


class FilterAgent(BaseAgent):
    """Agent responsible for filtering relevant articles."""

    def __init__(self, keywords: List[str] = ["AI", "robotics", "startup"]) -> None:
        self.keywords = [k.lower() for k in keywords]

    def process(self, items: List[Dict]) -> List[Dict]:
        filtered = []
        for item in items:
            title = item.get("title", "").lower()
            # Normalize keywords to lowercase list for comparison
            item_keywords = [k.lower() for k in item.get("keywords", [])]
            # Check if any self.keywords match in title or item keywords
            if any(
                keyword.lower() in title or keyword.lower() in item_keywords
                for keyword in self.keywords
            ):
                filtered.append(item)
        return filtered
