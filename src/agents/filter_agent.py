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
        "ai": [
            "AI",
            "artificial intelligence",
            "machine learning",
            "LLM",
            "neural",
            "deep learning",
        ],
        "ai": [
            "AI",
            "artificial intelligence",
            "machine learning",
            "LLM",
            "neural",
            "deep learning",
        ],
        "robotics": ["robotics", "robot", "automation", "autonomous"],
        "startup": [
            "startup",
            "founder",
            "venture",
            "startup opportunity",
            "investment",
        ],
        "trending": [
            "breakthrough",
            "launch",
            "raises",
            "open source",
            "new model",
            "benchmark",
            "research",
        ],
    }

    NOISE_KEYWORDS = {
        "newsletter",
        "opinion",
        "roundup",
        "weekly recap",
        "sponsored",
        "press release",
        "earnings call",
        "stock price",
        "celebrity",
        "gossip",
        "lifestyle",
        "how to use chatgpt",
        "beginner guide",
        "top 10 tools",
        "click here",
    }

    def __init__(
        self,
        categories: List[str] = None,
        signal_threshold: float = 0.0,
        noise_threshold: float = 0.5,
    ) -> None:
        """
        Initialize filter agent.

        Args:
            categories: List of category names to include (default: all)
            signal_threshold: Minimum match score (0.0-1.0) to keep article
            noise_threshold: Maximum noise score (0.0-1.0) to keep article
        """
        self.categories = categories or list(self.KEYWORD_CATEGORIES.keys())
        self.signal_threshold = signal_threshold
        self.noise_threshold = noise_threshold  # Adjust this value as needed
        self.keywords: Set[str] = set()

        # Build flat set of all keywords from selected categories
        for category in self.categories:
            if category in self.KEYWORD_CATEGORIES:
                self.keywords.update(
                    k.lower() for k in self.KEYWORD_CATEGORIES[category]
                )
            else:
                logger.warning(
                    f"Category '{category}' not found in KEYWORD_CATEGORIES. Adding to keywords directly."
                )
                logger.warning(
                    f"Category '{category}' not found in KEYWORD_CATEGORIES. Adding to keywords directly."
                )
                self.keywords.add(category.lower())

    def _calculate_match_score(self, article: Dict) -> float:
        """Calculate how well article matches keywords (0.0 to 1.0)."""
        title = article.get("title", "").lower()
        summary = article.get("summary", "").lower()
        text = f"{title} {summary}"

        matches = sum(1 for keyword in self.keywords if keyword in text)
        return min(matches / max(len(self.keywords), 1), 1.0)

    def process(self, items: List[Dict]) -> List[Dict]:
        """Filter and score articles."""
        filtered = []
        for item in items:
            signal_score = self._calculate_match_score(item)
            # Add noise score to penalize irrelevant articles
            noise_score = self.noise_score(item)  # Adjust weight of noise
            logger.info(
                f"Article: {item.get('title', '')[:30]}... | Signal Score: {signal_score:.2f} | Noise Score: {noise_score:.2f}"
            )
            if (
                signal_score >= self.signal_threshold
                and noise_score < self.noise_threshold
            ):
                item["filter_score"] = (signal_score, noise_score)
                filtered.append(item)
        logger.info(
            f"Filtered {len(filtered)} out of {len(items)} articles with thresholds: signal={self.signal_threshold}, noise={self.noise_threshold}"
        )
        return filtered

    def noise_score(self, article: dict) -> int:
        text = f"{article.get('title','')} {article.get('summary','')}".lower()

        score = 0

        for kw in self.NOISE_KEYWORDS:
            if kw in text:
                score += 1

        return score
