import json
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from src.database.database import Database, Founder, Opportunity
from openai import OpenAI
from .base_agent import BaseAgent
from src.utils.logger import get_logger

logger = get_logger("scoring_agent")


class ScoringAgent(BaseAgent):
    def __init__(self, model: str, db_hndlr: Database = None) -> None:
        self.client = OpenAI()
        self.model = model
        self.db_hndlr = db_hndlr

    def process(self, founder_name: str, args=None) -> List[Dict[str, Any]]:
        """Score a list of opportunity proposals in one request."""
        opportunities = self.db_hndlr.retrieve_items(Opportunity)
        if not opportunities:
            return []

        founders = self.db_hndlr.retrieve_items(Founder)
        founder_profile = next((f for f in founders if f.name == founder_name), None)
        prompt = self._build_batch_prompt(opportunities, founder_profile)
        response = self.client.responses.create(
            model=self.model,
            input=prompt,
        )
        content = response.output[0].content[0].text
        parsed_list = self._parse_batch_response(
            content, expected_len=len(opportunities)
        )

        scored = []
        for opp, score_data in zip(opportunities, parsed_list):
            setattr(opp, "market_size", score_data.get("market_size", 0))
            setattr(
                opp,
                "technical_advantage",
                score_data.get("technical_advantage", 0),
            )
            setattr(opp, "timing", score_data.get("timing", 0))
            setattr(
                opp,
                "founder_fit_score",
                score_data.get("founder_fit_score", 0),
            )
            setattr(opp, "defensibility", score_data.get("defensibility", 0))
            setattr(opp, "score", score_data.get("score", 0))
            setattr(opp, "final_score", self.compute_final_score(score_data))
            setattr(opp, "notes", score_data.get("notes", ""))
            self.db_hndlr.add_item(opp)

        self._persist_scores(scored)
        return [self._serialize_opportunity(opportunity) for opportunity in scored]

    @staticmethod
    def compute_final_score(score_data: Dict[str, Any]) -> float:
        return (
            score_data.get("market_size", 0) * 0.3
            + score_data.get("technical_advantage", 0) * 0.25
            + score_data.get("timing", 0) * 0.2
            + score_data.get("founder_fit_score", 0) * 0.15
            + score_data.get("defensibility", 0) * 0.1
        )

    def _build_batch_prompt(
        self,
        opportunities: List[Opportunity],
        founder: Optional[Founder],
    ) -> str:
        serialized_opportunities = [
            self._serialize_opportunity(opportunity) for opportunity in opportunities
        ]
        serialized_founder = self._serialize_founder(founder)

        return f"""
        You are a top-tier VC evaluating multiple startup opportunities.

        Opportunities:
        {json.dumps(serialized_opportunities, indent=2)}

        Founder profile:
        {json.dumps(serialized_founder, indent=2)}

        Score each opportunity from 1-10 on these dimensions:
        - market_size
        - technical_advantage
        - timing
        - founder_fit_score
        - defensibility

        Return ONLY valid JSON (list with same length as opportunities):
        [
          {{
          "score": int, 
          "market_size": int, 
          "technical_advantage": int, 
          "timing": int, 
          "founder_fit_score": int, 
          "defensibility": int, 
          "notes": "..."}},
        ]
        """

    def _parse_batch_response(
        self, content: str, expected_len: int
    ) -> List[Dict[str, Any]]:
        try:
            results = json.loads(content)
            if isinstance(results, list) and len(results) == expected_len:
                return results
        except Exception:
            pass

        return [
            {
                "score": 0,
                "market_size": 0,
                "technical_advantage": 0,
                "timing": 0,
                "founder_fit_score": 0,
                "defensibility": 0,
                "notes": "failed_to_parse",
            }
            for _ in range(expected_len)
        ]

    def _persist_scores(self, opportunities: List[Opportunity]) -> None:
        with Session(self.db_hndlr.get_engine()) as session:
            for opportunity in opportunities:
                session.merge(opportunity)
            session.commit()

    def _serialize_opportunity(self, opportunity: Opportunity) -> Dict[str, Any]:
        if hasattr(opportunity, "model_dump"):
            data = opportunity.model_dump(mode="json")
        else:
            data = dict(opportunity)

        data["name"] = data.get("title", "")
        return data

    def _serialize_founder(self, founder: Optional[Founder]) -> Dict[str, Any]:
        if founder is None:
            return {}
        if hasattr(founder, "model_dump"):
            return founder.model_dump(mode="json")
        return dict(founder)
