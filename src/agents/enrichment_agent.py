"""Enrichment agent for Tech Radar data.

This can be expanded with real LLM calls to summarize/annotate text.
"""

from typing import Dict, List
from urllib import response

import os

from src.utils.logger import get_logger
from .base_agent import BaseAgent
from openai import OpenAI

from dotenv import load_dotenv
import os

logger = get_logger("enrichment_agent")

load_dotenv()


class EnrichmentAgent(BaseAgent):
    """Agent responsible for enriching events with metadata."""

    def __init__(
        self, model: str = "gpt-placeholder", database_file: str = None
    ) -> None:
        self.client = OpenAI()
        self.model = model
        self.database_file = database_file

    def enrich(self, article):
        prompt = f"""
        You are a tech analyst.

        Analyze this article:

        TITLE: {article['title']}
        SUMMARY: {article['summary']}

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

    def process(self, items: List[Dict]) -> List[Dict]:
        enriched_list = []
        for item in items:
            if item["is_noise"]:
                item["enriched"] = "N/A"
            elif (
                "enriched" not in item.keys()
            ):  # Only enrich if not marked as noise or enriched field is missing
                enriched = self.enrich(item)
                item["enriched"] = enriched

            enriched_list.append(item)

        self.update_enrichment_database(enriched=enriched_list)
        return enriched_list

    def update_enrichment_database(self, enriched: List[Dict]) -> None:
        """Update the enrichment database with new entries, avoiding duplicates."""
        import json

        logger.info("Updating enrichment database with new articles.")

        with open(self.database_file, "r+") as f:
            json.dump(enriched, f, indent=2)
