from typing import List, Dict
from openai import OpenAI
import os
import json
import re

from .base_agent import BaseAgent
from dotenv import load_dotenv

load_dotenv()


class OpportunityAgent(BaseAgent):
    def __init__(self, model: str):
        self.client = OpenAI()
        self.model = model

    def process(
        self, enriched_articles: List[Dict], founder_profile: Dict
    ) -> List[Dict]:
        # Implement grouping of similar trends before sending to LLM
        grouped_articles = self._group_similar_trends(enriched_articles)
        prompt = self._build_prompt(grouped_articles, founder_profile)

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )

        content = response.output[0].content[0].text
        return self._parse_response(content)

    def _build_prompt(self, articles: List[Dict], founder: Dict) -> str:

        simplified = [
            {
                "title": a.get("title"),
                "summary": a.get("summary"),
                "tags": a.get("tags"),
            }
            for a in articles
        ]

        return f"""
        You are a top-tier deeptech VC.

        Analyze the following tech signals:

        {json.dumps(simplified, indent=2)}

        Founder profile:

        {json.dumps(founder, indent=2)}

        Identify 3-5 HIGH-CONVICTION startup opportunities.

        Rules:
        - Must be technically grounded
        - Must have a clear "why now"
        - Must have a clear understanding of the founder fit (if defined, otherwise indicate what founder profile would be ideal)
        - Provide a numerical "wedge" score (0-10) indicating how easy it would be for a startup to gain initial traction in this space, based on current competition and market awareness.

        Return STRICT JSON ONLY:

        [
        {{
            "name": "...",
            "description": "...",
            "why_now": "...",
            "founder_fit": "...",
            "wedge": "...",
            "wedge_score": "...",
            "risk": "...",
            "required_insight": "..."
        }}
        ]
        """

    def _parse_response(self, content: str) -> List[Dict]:

        try:
            return json.loads(content)
        except Exception:
            # try to extract JSON block
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass

            return [{"error": "failed_to_parse", "raw": content}]

    def _group_similar_trends(self, articles: List[Dict]) -> List[Dict]:
        sorted_articles = sorted(
            articles, key=lambda a: a.get("filter_score", 0), reverse=True
        )

        return sorted_articles[:15]
