"""
Daily pipeline orchestration.

Steps:
1. Ingest articles
2. Filter relevant ones
3. Enrich data
4. Generate opportunities
"""

import os
import sys
from typing import Dict, Any, List

from agents.scoring_agent import ScoringAgent
from config.config import load_config, get_config_value
from ingestion.rss_ingestion import fetch_rss_articles
from agents.filter_agent import FilterAgent
from agents.enrichment_agent import EnrichmentAgent
from agents.opportunity_agent import OpportunityAgent


import json


def ingest_articles(
    rss_urls: List[str],
    max_items: int = 50,
    is_mock: bool = False,
    database_file: str = None,
) -> List[Dict[str, Any]]:
    """Load config and fetch articles from RSS feeds."""
    return fetch_rss_articles(
        urls=rss_urls,
        max_items=max_items,
        is_mock=is_mock,
        database_file=database_file,
    )


def retrieve_database(database_file: str = None):
    with open(database_file, "r+") as f:
        database = json.load(f)
    return database


def run_daily_pipeline(
    founder_profile: Dict[str, Any] = {}, args=None
) -> Dict[str, Any]:
    """Orchestrate pipeline: ingest -> filter -> enrich -> opportunity."""

    cfg = load_config()

    is_mock = getattr(args, "dry_run", False)

    # Save logs and outputs in database as json
    database_file = (
        os.path.join(".tmp", getattr(args, "database_file"))
        if is_mock
        else getattr(args, "database_file")
    )
    output_file = (
        os.path.join(".tmp", getattr(args, "output_file"))
        if is_mock
        else getattr(args, "output_file")
    )
    # Ensure the directories exist for the database and output files
    os.makedirs(os.path.dirname(database_file), exist_ok=True)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    database_file = getattr(args, "database_file")

    max_items = 1 if is_mock else get_config_value(cfg, "ingestion.rss.max_items", 50)

    if getattr(args, "update_db", False):
        ingest_articles(
            rss_urls=get_config_value(cfg, "ingestion.rss.urls", []),
            max_items=max_items,
            is_mock=is_mock,
            database_file=database_file,
        )
    articles = retrieve_database(database_file)
    filter_agent = FilterAgent(
        signal_threshold=get_config_value(cfg, "agents.filter.signal_threshold"),
        noise_threshold=get_config_value(cfg, "agents.filter.noise_threshold"),
        database_file=database_file,
    )
    filtered = filter_agent.process(articles, args=args)

    # Create enrichment agent instance
    enrichment_agent = EnrichmentAgent(
        model=get_config_value(cfg, "agents.enrichment.model"),
        database_file=database_file,
    )
    enriched = enrichment_agent.process(filtered)

    if getattr(args, "generate_opp", False):
        # Create opportunity agent instance and generate ideas
        opportunity_agent = OpportunityAgent(
            model=get_config_value(cfg, "agents.opportunity.model")
        )
        opportunities = opportunity_agent.process(
            enriched, founder_profile=founder_profile
        )

        # Create a scoring agent instance and score the opportunities
        scoring_agent = ScoringAgent(
            model=get_config_value(cfg, "agents.scoring.model"), output_file=output_file
        )
        scored_opportunities = scoring_agent.process(opportunities, founder_profile)
    else:
        scored_opportunities = []

    if is_mock and not getattr(args, "keep_temp", False) and os.path.exists(".tmp"):
        try:
            os.rmdir(".tmp")
        except:
            pass

    return {
        "articles": articles,
        "filtered": filtered,
        "opportunities": scored_opportunities,
    }
