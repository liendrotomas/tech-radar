"""
Filter agent for Tech Radar.

- Input: list of articles
- Output: only relevant articles based on keyword categories
- Keyword-based filtering with extensible category system
"""

from datetime import datetime
from typing import List, Dict, Set

from src.database.database import Database, Feed
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
        "subscription",
        "war",
        "politics",
        "celebrity",
        "iran",
        "russia",
        "ukraine",
        "trump",
        "biden",
        "exclusive",
        "apps",
        "ios",
        "android",
        "events",
    }

    def __init__(
        self,
        categories: List[str] = None,
        filter_config: Dict[str, float] = None,
        db_hndlr: Database = None,
    ) -> None:
        """
        Initialize filter agent.

        Args:
            categories: List of category names to include (default: all)
            filter_config: Dictionary containing filter configuration
            db_hndlr: Database handler instance
        """
        self.categories = categories or list(self.KEYWORD_CATEGORIES.keys())
        self.signal_threshold = (
            filter_config.get("signal_threshold", 0.0) if filter_config else 0.0
        )
        self.noise_threshold = (
            filter_config.get("noise_threshold", 0.5) if filter_config else 0.5
        )  # Adjust this value as needed
        self.keywords: Set[str] = set()
        self.db_hndlr = db_hndlr

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
                self.keywords.add(category.lower())

    def _calculate_match_score(self, article: Feed) -> float:
        """Calculate how well article matches keywords (0.0 to 1.0)."""
        title = getattr(article, "title", "").lower()
        summary = getattr(article, "summary", "").lower()
        text = f"{title} {summary}"

        matches = sum(1 for keyword in self.keywords if keyword in text)
        return min(matches / max(len(self.keywords), 1), 1.0)

    def process(self, args=None) -> List[Feed]:
        """Filter and score articles."""
        items = self.db_hndlr.retrieve_items(Feed)
        filtered_items: List[Feed] = []
        for item in items:
            signal_score = self._calculate_match_score(item)
            noise_score = self.noise_score(item)
            logger.info(
                f"Article: {getattr(item, 'title', '')[:30]}... | Signal Score: {signal_score:.2f} | Noise Score: {noise_score:.2f}"
            )
            setattr(item, "signal_score", signal_score)
            setattr(item, "noise_score", noise_score)
            if (
                signal_score >= self.signal_threshold
                and noise_score < self.noise_threshold
            ):
                setattr(item, "is_noise", False)
                filtered_items.append(item)
            else:
                setattr(item, "is_noise", True)

            setattr(
                item,
                "processing_metadata",
                {
                    "last_processed": datetime.now().isoformat(),
                    "threshold_signal": self.signal_threshold,
                    "threshold_noise": self.noise_threshold,
                },
            )
            self.db_hndlr.add_item(item)

        logger.info(
            f"Filtered {len(filtered_items)} out of {len(items)} articles with thresholds: signal={self.signal_threshold}, noise={self.noise_threshold}"
        )
        return filtered_items

    def noise_score(self, article: dict) -> int:
        text = (
            f"{getattr(article, 'title', '')} {getattr(article, 'summary', '')} {getattr(article, 'keywords', '')}".lower()
        )

        score = 0

        for kw in self.NOISE_KEYWORDS:
            if kw in text:
                score += 1
        if getattr(article, "keywords", []) == []:
            score += 5  # Penalize articles with no keywords
        return score
