import json
import math
import re
from typing import Any, Dict, List, Optional
from collections import defaultdict

from src.database.services import FeedbackService
from openai import OpenAI
from sklearn.cluster import KMeans

from dotenv import load_dotenv
from utils.ai_tools import embedder

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

    def process(self, founder_name: Optional[str], args=None) -> List[Dict[str, Any]]:
        max_opps = getattr(args, "max_opps", None)
        items = self.db_hndlr.retrieve_items(Feed)
        filtered_articles = [item for item in items if not item.is_noise]
        if not filtered_articles:
            return []

        founders = self.db_hndlr.retrieve_items(Founder)
        founder_profile = next((f for f in founders if f.name == founder_name), None)

        grouped_articles = self._group_similar_trends(filtered_articles)

        feedback_service = FeedbackService(self.db_hndlr, founder_name)
        prompt = self._build_prompt(
            grouped_articles, founder_profile, max_opps, feedback_service
        )

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
        feedback_service: FeedbackService,
    ) -> str:
        simplified = [
            {
                "title": a.get("title"),
                "summary": a.get("summary"),
                "keywords": a.get("keywords", []),
            }
            for a in articles
        ]
        context = feedback_service.build_context(self.client, query_text=simplified)

        return f"""
        You are a top-tier deeptech VC.
        User preferences based on past decisions:
        {context}

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
                    raise ValueError(f"Failed to parse JSON from response: {content}")

            return [{"error": "failed_to_parse", "raw": content}]

    def summarize_group(group):
        rep = max(group, key=lambda a: getattr(a, "filter_score", 0))

        return {
            "title": rep.title,
            "summary": rep.summary[:300],
            "keywords": list(set(tag for a in group for tag in a.keywords)),
            "n_articles": len(group),
        }

    def _group_similar_trends(
        self, articles: List[Feed], max_items=60, max_groups=10
    ) -> List[Dict[str, Any]]:
        if not articles:
            return []

        # ---------- 1. PRE-FILTER ----------
        articles = [a for a in articles if getattr(a, "processed") == False]
        articles = sorted(
            articles,
            key=lambda a: getattr(a, "signal_score", 0) - getattr(a, "noise_score", 0),
            reverse=True,
        )[:max_items]

        if len(articles) == 1:
            a = articles[0]
            # Set processed to True to avoid re-processing in enrichment and opportunity generation
            setattr(a, "processed", True)
            return [
                {
                    "title": getattr(a, "title", ""),
                    "summary": getattr(a, "summary", "")[:300],
                    "keywords": list(getattr(a, "keywords", [])),
                    "n_articles": 1,
                }
            ]

        # ---------- 2. DEDUP ----------
        def dedup(articles):
            seen = set()
            out = []

            for a in articles:
                key = (getattr(a, "title", "")[:80]).lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(a)

            return out

        articles = dedup(articles)
        # ---------- 2. EMBEDDINGS ----------
        texts = [
            f"{getattr(a, 'title', '')} {getattr(a, 'summary', '')}" for a in articles
        ]

        embeddings = embedder(self.client, texts)

        # ---------- 3. ADAPTIVE K ----------
        k = max(2, min(max_groups, int(math.sqrt(len(articles)))))

        labels = KMeans(n_clusters=k, random_state=0, n_init="auto").fit_predict(
            embeddings
        )

        # ---------- 4. BUILD CLUSTERS ----------
        clusters = defaultdict(list)
        for a, l in zip(articles, labels):
            clusters[l].append(a)

        # ---------- 5. FILTER SMALL CLUSTERS ----------
        clusters = {l: g for l, g in clusters.items() if len(g) >= 2}

        # ---------- 6. SUMMARIZE ----------
        def summarize_group(group):
            rep = max(
                group,
                key=lambda a: getattr(a, "signal_score", 0)
                - getattr(a, "noise_score", 0),
            )

            return {
                "title": getattr(rep, "title", ""),
                "summary": getattr(rep, "summary", "")[:300],
                "keywords": list(
                    set(tag for a in group for tag in getattr(a, "keywords", []))
                ),
                "n_articles": len(group),
            }

        groups = [summarize_group(g) for g in clusters.values()]
        # ---------- 7. SORT & LIMIT ----------
        groups = sorted(groups, key=lambda g: g["n_articles"], reverse=True)[
            :max_groups
        ]
        # For the feeds used in opportunity generation, set processed to True to avoid re-processing in enrichment and opportunity generation
        for g in groups:
            for a in articles:
                if getattr(a, "title", "") == g["title"]:
                    setattr(a, "processed", True)
                    self.db_hndlr.update_item(a)
                    break

        return groups

    def _serialize_opportunity(self, opportunity: Opportunity) -> Dict[str, Any]:
        data = opportunity.model_dump(mode="json")
        data["name"] = data.get("title", "")
        return data
