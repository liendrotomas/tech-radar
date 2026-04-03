"""
Daily pipeline orchestration.

Steps:
1. Ingest articles
2. Filter relevant ones
3. Enrich data
4. Generate opportunities
"""

from typing import Dict, Any, List

from config.config import load_config, get_config_value
from ingestion.rss_ingestion import fetch_rss_articles
from agents.filter_agent import FilterAgent
from agents.enrichment_agent import EnrichmentAgent
from agents.opportunity_agent import OpportunityAgent

def ingest_articles() -> List[Dict[str, Any]]:
    """Load config and fetch articles from RSS feeds."""
    cfg = load_config()
    rss_urls = get_config_value(cfg, "ingestion.rss.urls", [])
    max_items = get_config_value(cfg, "ingestion.rss.max_items", 50)
    return fetch_rss_articles(urls=rss_urls, max_items=max_items)


def run_daily_pipeline(founder_profile: Dict[str, Any] = None) -> Dict[str, Any]:
    """Orchestrate pipeline: ingest -> filter -> enrich -> opportunity."""
    founder_profile = founder_profile or {}

    articles = ingest_articles()
    cfg = load_config()

    filter_agent = FilterAgent(categories=["ai", "robotics", "startup"], threshold=get_config_value(cfg, "agents.filter.threshold", 0.1))
    filtered = filter_agent.process(articles)
    top_articles = sorted(filtered, key=lambda x: x["filter_score"], reverse=True)[:5]

    # Create enrichment agent instance
    enrichment_agent = EnrichmentAgent(model=get_config_value(cfg, "agents.enrichment.model", "gpt-placeholder"))
    enriched = enrichment_agent.process(top_articles)

    # Create opportunity agent instance and generate ideas
    opportunity_agent = OpportunityAgent(model=get_config_value(cfg, "agents.opportunity.model", "gpt-placeholder"))
    opportunities = opportunity_agent.process(enriched, founder_profile=founder_profile)
    
    return {
        "articles": articles,
        "filtered": filtered,
        "opportunities": opportunities,
    }
