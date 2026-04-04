from typing import List, Dict
from openai import OpenAI
import json
import re
from .base_agent import BaseAgent


class ScoringAgent(BaseAgent):
    def __init__(self, model: str):
        self.client = OpenAI()
        self.model = model

    def process(self, opportunities: List[Dict], founder_profile: Dict) -> List[Dict]:
        """Score a list of opportunity proposals in one request."""
        if not opportunities:
            return []

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
            record = score_data.copy()
            record["original"] = opp
            scored.append(record)

        return sorted(scored, key=lambda x: x.get("score", 0), reverse=True)

    def _build_batch_prompt(self, opportunities: List[Dict], founder: Dict) -> str:
        return f"""
        You are a top-tier VC evaluating multiple startup opportunities.

        Opportunities:
        {json.dumps(opportunities, indent=2)}

        Founder profile:
        {json.dumps(founder, indent=2)}

        Score each opportunity from 1-10 on these dimensions:
        - market_size
        - technical_advantage
        - timing
        - founder_fit
        - defensibility

        Return ONLY valid JSON (list with same length as opportunities):
        [
          {{
          "name": str,
          "score": int, 
          "market_size": int, 
          "technical_advantage": int, 
          "timing": int, 
          "founder_fit": int, 
          "defensibility": int, 
          "notes": "..."}},
        ]
        """

    def _parse_batch_response(self, content: str, expected_len: int) -> List[Dict]:
        import json

        try:
            results = json.loads(content)

            # validar formato
            if isinstance(results, list) and len(results) == expected_len:
                return results

        except Exception:
            pass

        # fallback seguro
        return [
            {
                "name": "N/A",
                "score": 0,
                "market_size": 0,
                "technical_advantage": 0,
                "timing": 0,
                "founder_fit": 0,
                "defensibility": 0,
                "notes": "failed_to_parse",
            }
            for _ in range(expected_len)
        ]

    def _build_prompt(self, opp: Dict, founder: Dict) -> str:

        return f"""
        You are a top-tier VC evaluating a startup idea.

        Opportunity:
        {json.dumps(opp, indent=2)}

        Founder:
        {json.dumps(founder, indent=2)}

        Score this opportunity from 1-10 on:

        - market_size
        - technical_advantage
        - timing
        - founder_fit
        - defensibility

        Return ONLY JSON:

        {{
        "name": str,
        "score": int,
        "market_size": int,
        "technical_advantage": int,
        "timing": int,
        "founder_fit": int,
        "defensibility": int,
        "notes": "short explanation"
        }}
        """

    def _parse_response(self, content: str) -> Dict:
        try:
            return json.loads(content)
        except Exception:
            match = re.search(r"\{.*\}", content, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except Exception:
                    pass

        return {"score": 0, "error": "failed_to_parse", "raw": content}
