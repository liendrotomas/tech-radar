"""
Opportunity agent.

- Input: filtered articles + founder profile
- Output: list of startup ideas

For now:
- generate simple mock ideas based on article titles
"""

from typing import List, Dict, Any

from src.utils.logger import get_logger
from .base_agent import BaseAgent

logger = get_logger("opportunity_agent")


class OpportunityAgent(BaseAgent):
    """Agent responsible for generating startup ideas from articles."""

    def __init__(self, model: str = "gpt-placeholder") -> None:
        self.model = model
        logger.info(f"Initializing OpportunityAgent with model: {self.model}")

    def _mock_generate_ideas(self, article: Dict, founder_profile: Dict) -> List[Dict]:
        title = article.get("title", "Unknown topic")
        ideas = [
            {
                "idea": f"Startup idea based on '{title}' for {founder_profile.get('name', 'a founder')}",
                "description": f"This idea is inspired by the article '{title}' and the founder's profile.",
            }
        ]
        return ideas

    def process(self, items: List[Dict], founder_profile: Dict) -> List[Dict]:
        all_ideas = []
        for item in items:
            ideas = self._mock_generate_ideas(item, founder_profile)
            all_ideas.extend(ideas)
        return all_ideas
