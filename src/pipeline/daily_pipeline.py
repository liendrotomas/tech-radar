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

from src.agents.scoring_agent import ScoringAgent
from src.config.config import load_config, get_config_value
from src.ingestion.rss_ingestion import fetch_rss_articles
from src.agents.filter_agent import FilterAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.opportunity_agent import OpportunityAgent
from src.database.database import Database, Founder
from src.utils.logger import get_logger

logger = get_logger("daily_pipeline")

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

    # Ensure the directories exist for the database and output files
    os.makedirs(os.path.dirname(database_file), exist_ok=True)

    # Initialize the database if it doesn't exist
    database_file = getattr(args, "database_file")
    db_hndlr = Database(database_file, recreate_on_schema_change=getattr(args, "recreate_on_schema_change", False))

    if founder_profile.get("name", None) in db_hndlr.retrieve_items(Founder.name):
        logger.warning("Founder profile already exists in database, skipping profile setup.")
    else:    
        founder = Founder()
        setattr(founder, "name", founder_profile.get("name", "founder"))
        setattr(
            founder, "profile", {k: v for k, v in founder_profile.items() if k != "name"}
        )
        logger.info(f"Founder profile {founder_profile.get('name')} added to database.")
        db_hndlr.add_item(founder)

    max_items = 1 if is_mock else get_config_value(cfg, "ingestion.rss.max_items", 50)

    if getattr(args, "update_db", False):
        """Load config and fetch articles from RSS feeds."""
        fetch_rss_articles(
            urls=get_config_value(cfg, "ingestion.rss.urls", []),
            max_items=max_items,
            db_hndlr=db_hndlr,
        )

    filter_agent = FilterAgent(
        filter_config=get_config_value(cfg, "agents.filter"),
        db_hndlr=db_hndlr,
    )
    filtered = filter_agent.process(args=args)

    # Create enrichment agent instance
    enrichment_agent = EnrichmentAgent(
        model=get_config_value(cfg, "agents.enrichment.model"),
        db_hndlr=db_hndlr,
    )
    enrichment_agent.process(filtered)

    if getattr(args, "generate_opp", False):
        # Create opportunity agent instance and generate ideas
        opportunity_agent = OpportunityAgent(
            model=get_config_value(cfg, "agents.opportunity.model"),
            db_hndlr=db_hndlr,
        )
        opportunities = opportunity_agent.process(founder_name=founder_profile.get("name", None), args=args)

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
