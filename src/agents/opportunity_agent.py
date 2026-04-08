from typing import List, Dict
from src.database.database import Database, Feed, Founder, Opportunity
from openai import OpenAI
import os
import json
import re

from .base_agent import BaseAgent
from dotenv import load_dotenv
from src.utils.logger import get_logger

from sklearn.cluster import KMeans
import numpy as np

logger = get_logger("opportunity_agent")

load_dotenv()


class OpportunityAgent(BaseAgent):
    def __init__(self, model: str, db_hndlr: Database = None) -> None:
        self.client = OpenAI()
        self.model = model
        self.db_hndlr = db_hndlr

    def embedder(self, texts):
        res = self.client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [e.embedding for e in res.data]

    def process(self, founder_name, args=None) -> None:
        items = self.db_hndlr.retrieve_items(Feed)
        filtered_articles = [item for item in items if not item.is_noise]
        
        founders = self.db_hndlr.retrieve_items(Founder)
        founder_profile = next((f for f in founders if f.name == founder_name), None)
        
        # Implement grouping of similar trends before sending to LLM
        grouped_articles = self._group_similar_trends(filtered_articles)
        prompt = self._build_prompt(grouped_articles, founder_profile)

        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        content = response.output[0].content[0].text
        parsed_response = self._parse_response(content)
        for opp in parsed_response:
            opportunity = Opportunity()
            setattr(opportunity, "founder_name", founder_name)
            setattr(opportunity, "title", opp.get("name", ""))
            setattr(opportunity, "description", opp.get("description", ""))
            setattr(opportunity, "score", opp.get("score", 0))
            setattr(opportunity, "why_now", opp.get("why_now", ""))
            setattr(opportunity, "founder_fit", opp.get("founder_fit", ""))
            setattr(opportunity, "wedge", opp.get("wedge", ""))
            setattr(opportunity, "wedge_score", opp.get("wedge_score", 0))
            setattr(opportunity, "risk", opp.get("risk", ""))
            setattr(opportunity, "required_insight", opp.get("required_insight", ""))
            self.db_hndlr.add_item(opportunity)

    def _build_prompt(self, articles: List[Dict], founder: Dict) -> str:

        simplified = [
            {
                "title": a.get("title"),
                "summary": a.get("summary"),
                "keywords": a.get("keywords", []),
            }
            for a in articles
        ]

        return f"""
        You are a top-tier deeptech VC.

        Analyze the following tech signals where the signals are organized into groups of similar trends. 
        Each signal has a title, summary, and keywords and multiple titles and summaries are combined together if they are similar separating them with a "/". 
        The first title corresponds to the first summary, and so on. 
        The keywords are a list of important tags associated with the signal:

        {json.dumps(simplified, indent=2)}

        Founder profile:

        {json.dumps(getattr(founder,"profile", {}), indent=2)}

        Identify two or more HIGH-CONVICTION startup opportunities.

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

    def _group_similar_trends(self, articles):
        # Filter out articles if is_noise field is true
        articles = [a for a in articles if not getattr(a, "is_noise", False)]
        texts = [getattr(a, "title", "") + " " + getattr(a, "summary", "") for a in articles]

        embeddings = self.embedder(texts)  # shape: (n, d)

        k = min(10, len(articles))
        labels = KMeans(n_clusters=k, random_state=0).fit_predict(embeddings)

        clusters = {}
        for a, l in zip(articles, labels):
            clusters.setdefault(l, []).append(a)

        # For each cluster, combine the articles into a single article with concatenated titles and summaries, and merged keywords
        for l, group in clusters.items():
            clusters[l] = {
                "title": " / ".join(set(getattr(a, "title", "") for a in group)),
                "summary": " / ".join(set(getattr(a, "summary", "") for a in group)),
                "keywords": list(
                    set(tag for a in group for tag in getattr(a, "keywords", []))
                ),
            }

        return list(clusters.values())
