import json
import re
from typing import Any, Dict, List, Optional

from openai import OpenAI
from sklearn.cluster import KMeans

from dotenv import load_dotenv

from src.database.database import Database, Feed, Founder, Opportunity
from src.utils.logger import get_logger
from .base_agent import BaseAgent

logger = get_logger("opportunity_agent")

load_dotenv()


class OpportunityAgent(BaseAgent):
    def __init__(self, model: str, db_hndlr: Database = None) -> None:
        self.client = OpenAI()
        self.model = model
        self.db_hndlr = db_hndlr

    def embedder(self, texts: List[str]) -> List[List[float]]:
        res = self.client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [e.embedding for e in res.data]

    def process(self, founder_name: Optional[str], args=None) -> List[Dict[str, Any]]:
        max_opps = getattr(args, "max_opps", None)
        items = self.db_hndlr.retrieve_items(Feed)
        filtered_articles = [item for item in items if not item.is_noise]
        if not filtered_articles:
            return []

        founders = self.db_hndlr.retrieve_items(Founder)
        founder_profile = next((f for f in founders if f.name == founder_name), None)

        grouped_articles = self._group_similar_trends(filtered_articles)
        prompt = self._build_prompt(grouped_articles, founder_profile, max_opps)

        logger.info("Generating opportunities")
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        content = response.output[0].content[0].text
        parsed_response = self._parse_response(content)
        persisted_opportunities: List[Dict[str, Any]] = []

        for opp in parsed_response:
            opportunity = Opportunity(
                founder_name=founder_name or "",
                title=opp.get("name", ""),
                description=opp.get("description", ""),
                why_now=opp.get("why_now", ""),
                founder_fit=opp.get("founder_fit", ""),
                wedge=opp.get("wedge", ""),
                wedge_score=float(opp.get("wedge_score", 0) or 0),
                risk=opp.get("risk", ""),
                required_insight=opp.get("required_insight", ""),
            )
            self.db_hndlr.add_item(opportunity)
            persisted_opportunities.append(self._serialize_opportunity(opportunity))

        return persisted_opportunities

    def _build_prompt(
        self,
        articles: List[Dict[str, Any]],
        founder: Optional[Founder],
        max_opps: Optional[int],
    ) -> str:

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

        {json.dumps(getattr(founder, "profile", {}), indent=2)}

        Identify up to {max_opps}, or less, HIGH-CONVICTION startup opportunities.

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

    def _parse_response(self, content: str) -> List[Dict[str, Any]]:

        try:
            parsed = json.loads(content)
            if isinstance(parsed, list):
                return parsed
        except Exception:
            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass

            return [{"error": "failed_to_parse", "raw": content}]

    def _group_similar_trends(self, articles: List[Feed]) -> List[Dict[str, Any]]:
        if not articles:
            return []

        if len(articles) == 1:
            article = articles[0]
            return [
                {
                    "title": getattr(article, "title", ""),
                    "summary": getattr(article, "summary", ""),
                    "keywords": list(getattr(article, "keywords", [])),
                }
            ]

        texts = [
            getattr(a, "title", "") + " " + getattr(a, "summary", "") for a in articles
        ]

        embeddings = self.embedder(texts)

        k = min(10, len(articles))
        labels = KMeans(n_clusters=k, random_state=0).fit_predict(embeddings)

        clusters = {}
        for a, l in zip(articles, labels):
            clusters.setdefault(l, []).append(a)

        for l, group in clusters.items():
            clusters[l] = {
                "title": " / ".join(set(getattr(a, "title", "") for a in group)),
                "summary": " / ".join(set(getattr(a, "summary", "") for a in group)),
                "keywords": list(
                    set(tag for a in group for tag in getattr(a, "keywords", []))
                ),
            }

        return list(clusters.values())

    def _serialize_opportunity(self, opportunity: Opportunity) -> Dict[str, Any]:
        data = opportunity.model_dump(mode="json")
        data["name"] = data.get("title", "")
        return data
