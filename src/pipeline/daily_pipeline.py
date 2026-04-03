"""
Daily pipeline orchestration.

Steps:
1. Ingest articles
2. Filter relevant ones
3. Enrich data
4. Generate opportunities
"""

from typing import Dict, Any, List

from agents.scoring_agent import ScoringAgent
from config.config import load_config, get_config_value
from ingestion.rss_ingestion import fetch_rss_articles
from agents.filter_agent import FilterAgent
from agents.enrichment_agent import EnrichmentAgent
from agents.opportunity_agent import OpportunityAgent


def ingest_articles(rss_urls: List[str], max_items: int = 50) -> List[Dict[str, Any]]:
    """Load config and fetch articles from RSS feeds."""
    return fetch_rss_articles(urls=rss_urls, max_items=max_items)


def run_daily_pipeline(
    founder_profile: Dict[str, Any] = None, args=None
) -> Dict[str, Any]:
    """Orchestrate pipeline: ingest -> filter -> enrich -> opportunity."""
    cfg = load_config()

    is_mock = getattr(args, "dry_run", False)
    founder_profile = founder_profile or {}

    max_items = 1 if is_mock else get_config_value(cfg, "ingestion.rss.max_items", 50)

    articles = ingest_articles(
        rss_urls=get_config_value(cfg, "ingestion.rss.urls", []), max_items=max_items
    )

    cfg = load_config()

    filter_agent = FilterAgent(
        signal_threshold=get_config_value(cfg, "agents.filter.signal_threshold", 0.1),
        noise_threshold=get_config_value(cfg, "agents.filter.noise_threshold", 0.5),
    )
    filtered = filter_agent.process(articles)
    top_articles = sorted(filtered, key=lambda x: x["filter_score"], reverse=True)[:5]
    # Create enrichment agent instance
    enrichment_agent = EnrichmentAgent(
        model=get_config_value(cfg, "agents.enrichment.model")
    )
    enriched = enrichment_agent.process(top_articles)

    # Create opportunity agent instance and generate ideas
    opportunity_agent = OpportunityAgent(
        model=get_config_value(cfg, "agents.opportunity.model")
    )
    opportunities = opportunity_agent.process(enriched, founder_profile=founder_profile)

    # Create a scoring agent instance and score the opportunities
    scoring_agent = ScoringAgent(model=get_config_value(cfg, "agents.scoring.model"))
    scored_opportunities = scoring_agent.process(opportunities, founder_profile)

    return {
        "articles": articles,
        "filtered": filtered,
        "opportunities": scored_opportunities,
    }
