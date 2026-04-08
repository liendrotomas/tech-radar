"""Enrichment agent for Tech Radar data.

This can be expanded with real LLM calls to summarize/annotate text.
"""

from typing import Dict, List

from src.database.database import Database, Feed

from src.utils.logger import get_logger
from .base_agent import BaseAgent
from openai import OpenAI

from dotenv import load_dotenv

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

        import json

        try:
            return json.loads(text)
        except:
            return {"raw": text}

    def process(self, args=None) -> None:
        items = self.db_hndlr.retrieve_items(Feed)
        for item in items:
            if getattr(item, "is_noise", False):
                setattr(item, "enriched", "N/A")
            elif not getattr(
                item, "enriched", None
            ):  # Only enrich if not marked as noise or enriched field is missing
                enriched = self.enrich(item)
                setattr(item, "enriched", enriched)

            self.db_hndlr.add_item(
                item
            )  # Update the item in the database with new enrichment data
