"""
Filter agent for Tech Radar.

- Input: list of articles
- Output: only relevant articles based on keyword categories
- Keyword-based filtering with extensible category system
"""

from typing import List, Dict, Set
from .base_agent import BaseAgent
from src.utils.logger import get_logger

logger = get_logger("filter_agent")

class FilterAgent(BaseAgent):
    """Filter articles by relevant technology keywords."""

    # Define keyword categories for easy extension
    KEYWORD_CATEGORIES = {
        "ai": ["AI", "artificial intelligence", "machine learning", "LLM", "neural", "deep learning"],
        "robotics": ["robotics", "robot", "automation", "autonomous"],
        "startup": ["startup", "founder", "venture", "startup opportunity", "investment"],
    }

    def __init__(self, categories: List[str] = None, threshold: float = 0.0) -> None:
        """
        Initialize filter agent.
        
        Args:
            categories: List of category names to include (default: all)
            threshold: Minimum match score (0.0-1.0) to keep article
        """
        self.categories = categories or list(self.KEYWORD_CATEGORIES.keys())
        self.threshold = threshold
        self.keywords: Set[str] = set()

        # Build flat set of all keywords from selected categories
        for category in self.categories:
            if category in self.KEYWORD_CATEGORIES:
                self.keywords.update(
                    k.lower() for k in self.KEYWORD_CATEGORIES[category]
                )
            else:
                logger.warning(f"Category '{category}' not found in KEYWORD_CATEGORIES. Adding to keywords directly.")
                self.keywords.add(category.lower())

    def _calculate_match_score(self, article: Dict) -> float:
        """Calculate how well article matches keywords (0.0 to 1.0)."""
        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()
        text = f"{title} {summary}"
        
        matches = sum(1 for keyword in self.keywords if keyword in text)
        logger.info(f"Article: {title[:30]}... | Matches: {matches} | Score: {matches / max(len(self.keywords), 1):.2f}")
        return min(matches / max(len(self.keywords), 1), 1.0)

    def process(self, items: List[Dict]) -> List[Dict]:
        """Filter and score articles."""
        filtered = []
        for item in items:
            score = self._calculate_match_score(item)
            if score >= self.threshold:
                item["filter_score"] = score
                filtered.append(item)
        logger.info(f"Filtered {len(filtered)} out of {len(items)} articles with threshold {self.threshold}")
        return filtered

