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

    def __init__(self, keywords: List[str] = None) -> None:
        self.keywords = keywords or ["AI", "robotics", "startup"]

    def process(self, items: List[Dict]) -> List[Dict]:
        filtered = []
        for item in items:
            title = item.get("title", "").lower()
            summary = item.get("summary", "").lower()
            if any(keyword.lower() in title or keyword.lower() in summary for keyword in self.keywords):
                filtered.append(item)
        return filtered