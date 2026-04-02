"""Enrichment agent for Tech Radar data.

This can be expanded with real LLM calls to summarize/annotate text.
"""

from typing import Dict, List

from .base_agent import BaseAgent


class EnrichmentAgent(BaseAgent):
    """Agent responsible for enriching events with metadata."""

    def __init__(self, model: str = "gpt-placeholder") -> None:
        self.model = model

    def _mock_enrich(self, item: Dict) -> Dict:
        item = item.copy()
        item["summary"] = item.get("description", "")[:180]
        item["tags"] = ["emerging", "ai"]
        item["entities"] = ["startup", "technology"]
        return item

    def process(self, items: List[Dict]) -> List[Dict]:
        enriched = [self._mock_enrich(item) for item in items]
        return enriched
