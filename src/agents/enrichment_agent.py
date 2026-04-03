"""Enrichment agent for Tech Radar data.

This can be expanded with real LLM calls to summarize/annotate text.
"""

from typing import Dict, List
from urllib import response

import os
from .base_agent import BaseAgent
from openai import OpenAI

from dotenv import load_dotenv
import os

load_dotenv()


class EnrichmentAgent(BaseAgent):
    """Agent responsible for enriching events with metadata."""

    def __init__(self, model: str = "gpt-placeholder") -> None:
        self.client = OpenAI()
        self.model = model

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
        enriched = [self.enrich(item) for item in items]
        return enriched
