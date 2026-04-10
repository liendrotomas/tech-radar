"""Enrichment agent for Tech Radar data."""

import json
from typing import Any, Dict

from src.database.database import Database, Feed
from openai import OpenAI
from dotenv import load_dotenv

from src.utils.logger import get_logger
from .base_agent import BaseAgent

logger = get_logger("enrichment_agent")

load_dotenv()


class EnrichmentAgent(BaseAgent):
    """Agent responsible for enriching events with metadata."""

    def __init__(
        self, model: str = "gpt-placeholder", db_hndlr: Database = None
    ) -> None:
        self.client = OpenAI()
        self.model = model
        self.db_hndlr = db_hndlr

    def enrich(self, article):
        prompt = f"""
        You are a tech analyst.

        Analyze this article:

        TITLE: {getattr(article, 'title', '')}
        SUMMARY: {getattr(article, 'summary', '')}

        Return:
        - what: (1 sentence)
        - why: (1 sentence)
        - opportunity: (1 idea)
        - tags: (list)

        Be concise, specific, and avoid generic startup ideas.
        Focus on actionable opportunities.
        Return only valid dictionary ready for parsing with the specified fields: what, why, opportunity, tags.
        """

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        text = response.output[0].content[0].text

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            logger.warning("Failed to parse enrichment response as JSON.")
            return {"raw": text}

    def _default_enrichment(self, article: Feed) -> Dict[str, Any]:
        return {
            "what": "Filtered as noise",
            "why": "Article did not meet signal/noise thresholds",
            "opportunity": "",
            "tags": list(getattr(article, "keywords", [])),
        }

    def process(self, args=None) -> list[Feed]:
        items = self.db_hndlr.retrieve_items(Feed)
        for item in items:
            if getattr(item, "is_noise", False):
                setattr(item, "enriched", self._default_enrichment(item))
            elif not getattr(item, "enriched", None):
                enriched = self.enrich(item)
                setattr(item, "enriched", enriched)

            self.db_hndlr.add_item(item)

        return items
