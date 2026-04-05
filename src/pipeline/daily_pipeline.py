"""
Daily pipeline orchestration.

Steps:
1. Ingest articles
2. Filter relevant ones
3. Enrich data
4. Generate opportunities
"""

import os
from typing import Dict, Any, List

from agents.scoring_agent import ScoringAgent
from config.config import load_config, get_config_value
from ingestion.rss_ingestion import fetch_rss_articles
from agents.filter_agent import FilterAgent
from agents.enrichment_agent import EnrichmentAgent
from agents.opportunity_agent import OpportunityAgent

from utils.database import (
    update_opportunity_database,
    log_pipeline_run,
)


def ingest_articles(
    rss_urls: List[str],
    max_items: int = 50,
    update_db: bool = False,
    is_mock: bool = False,
) -> List[Dict[str, Any]]:
    """Load config and fetch articles from RSS feeds."""
    return fetch_rss_articles(
        urls=rss_urls, max_items=max_items, update_db=update_db, is_mock=is_mock
    )


def run_daily_pipeline(
    founder_profile: Dict[str, Any] = {}, args=None
) -> Dict[str, Any]:
    """Orchestrate pipeline: ingest -> filter -> enrich -> opportunity."""
    cfg = load_config()

    is_mock = getattr(args, "dry_run", False)

    max_items = 1 if is_mock else get_config_value(cfg, "ingestion.rss.max_items", 50)

    articles = ingest_articles(
        rss_urls=get_config_value(cfg, "ingestion.rss.urls", []),
        max_items=max_items,
        update_db=getattr(args, "update_db", False),
        is_mock=is_mock,
    )

    filter_agent = FilterAgent(
        signal_threshold=get_config_value(cfg, "agents.filter.signal_threshold"),
        noise_threshold=get_config_value(cfg, "agents.filter.noise_threshold"),
    )
    filtered = filter_agent.process(articles)

    # Create enrichment agent instance
    enrichment_agent = EnrichmentAgent(
        model=get_config_value(cfg, "agents.enrichment.model")
    )
    enriched = enrichment_agent.process(filtered)

    # Create opportunity agent instance and generate ideas
    opportunity_agent = OpportunityAgent(
        model=get_config_value(cfg, "agents.opportunity.model")
    )
    opportunities = opportunity_agent.process(enriched, founder_profile=founder_profile)

    # Create a scoring agent instance and score the opportunities
    scoring_agent = ScoringAgent(model=get_config_value(cfg, "agents.scoring.model"))
    scored_opportunities = scoring_agent.process(opportunities, founder_profile)

    # Save logs and outputs in database as json
    if args.update_db:
        output_file = (
            os.path.join(".tmp", "mock", "opportunities.json")
            if is_mock
            else os.path.join(
                "outputs",
                f"{founder_profile.get('name', 'unknown')}",
                "opportunities.json",
            )
        )
        log_pipeline_file = (
            os.path.join(".tmp", "mock", "log_pipeline.json")
            if is_mock
            else os.path.join(
                "outputs",
                f"{founder_profile.get('name', 'unknown')}",
                "log_pipeline.json",
            )
        )
        update_opportunity_database(scored_opportunities, output_file=output_file)
        log_pipeline_run(
            log_data={
                "articles_count": len(articles),
                "filtered_count": len(filtered),
                "opportunities_count": len(scored_opportunities),
            },
            log_file=log_pipeline_file,
        )

    return {
        "articles": articles,
        "filtered": filtered,
        "opportunities": scored_opportunities,
    }
