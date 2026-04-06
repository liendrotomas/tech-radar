"""
Filter agent for Tech Radar.

- Input: list of articles
- Output: only relevant articles based on keyword categories
- Keyword-based filtering with extensible category system
"""

from datetime import datetime
import os
import sys
from typing import List, Dict, Set

from ingestion.rss_ingestion import CLEANUP_FUNCTIONS
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
    }

    def __init__(
        self,
        categories: List[str] = None,
        signal_threshold: float = 0.0,
        noise_threshold: float = 0.5,
        database_file: str = None,
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
        self.database_file = database_file

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

    def process(self, items: List[Dict], args=None) -> List[Dict]:
        """Filter and score articles."""
        filtered = []
        for item in items:
            signal_score = self._calculate_match_score(item)
            # Add noise score to penalize irrelevant articles
            noise_score = self.noise_score(item)  # Adjust weight of noise
            logger.info(
                f"Article: {item.get('title', '')[:30]}... | Signal Score: {signal_score:.2f} | Noise Score: {noise_score:.2f}"
            )
            item["signal_score"] = signal_score
            item["noise_score"] = noise_score
            if (
                signal_score >= self.signal_threshold
                and noise_score < self.noise_threshold
            ):
                item["is_noise"] = False
            else:
                item["is_noise"] = True
                # Optionally include low-scoring articles with a flag instead of filtering out completely

            item["processing_metadata"] = (
                {
                    "last_processed": datetime.now().isoformat(),
                    "threshold_signal": self.signal_threshold,
                    "threshold_noise": self.noise_threshold,
                },
            )
            filtered.append(item)

        logger.info(
            f"Filtered {len(filtered)} out of {len(items)} articles with thresholds: signal={self.signal_threshold}, noise={self.noise_threshold}"
        )

        if args.update_db:
            self.update_filter_database(filtered)
        # return only non-noise articles for next steps, but could also return all with flags if desired
        return filtered

    def noise_score(self, article: dict) -> int:
        text = f"{article.get('title','')} {article.get('summary','')}".lower()

        score = 0

        for kw in self.NOISE_KEYWORDS:
            if kw in text:
                score += 1

        return score

    def update_filter_database(self, filtered: List[Dict]) -> None:
        """Update the feed database with new entries, avoiding duplicates."""
        import json

        logger.info("Updating filtered database with new articles.")

        with open(self.database_file, "r+") as f:
            json.dump(filtered, f, indent=2)
