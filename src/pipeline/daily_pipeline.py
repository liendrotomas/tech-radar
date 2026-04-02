"""
Daily pipeline orchestration.

Steps:
1. Ingest articles
2. Filter relevant ones
3. Enrich data
4. Generate opportunities
"""

from typing import Dict, Any, List

from ingestion.rss_ingestion import fetch_rss_articles
from agents.filter_agent import FilterAgent
from agents.enrichment_agent import EnrichmentAgent
from agents.opportunity_agent import OpportunityAgent


def ingest_articles() -> List[Dict[str, Any]]:
    """Simple ingestion placeholder for one or more RSS feeds."""
    # Minimal valid flow path. In real code, use config+error handling.
    urls = ["https://example.com/ai-framework"]
    return fetch_rss_articles(urls=urls, max_items=10)


def run_daily_pipeline(founder_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """Orchestrate pipeline: ingest -> filter -> enrich -> opportunity."""
    founder_profile = founder_profile or {}

    articles = ingest_articles()

    filter_agent = FilterAgent(keywords=["AI", "emerging tech"])
    filtered = filter_agent.process(articles)

    opportunity_agent = OpportunityAgent(model="gpt-placeholder")
    opportunities = opportunity_agent.process(filtered, founder_profile=founder_profile)

    return {
        "articles": articles,
        "filtered": filtered,
        "opportunities": opportunities,
    }
