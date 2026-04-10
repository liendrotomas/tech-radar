import os
from typing import Any, Dict, Optional

from src.agents.scoring_agent import ScoringAgent
from src.agents.opportunity_agent import OpportunityAgent
from src.agents.enrichment_agent import EnrichmentAgent
from src.agents.filter_agent import FilterAgent
from src.config.config import load_config, get_config_value
from src.database.database import Database, Feed, Founder
from src.ingestion.rss_ingestion import fetch_rss_articles
from src.utils.logger import get_logger

logger = get_logger("daily_pipeline")


def _ensure_parent_dir(file_path: str) -> None:
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)


def _serialize_model(item: Any) -> Dict[str, Any]:
    if hasattr(item, "model_dump"):
        data = item.model_dump(mode="json")
        if "title" in data and "name" not in data:
            data["name"] = data["title"]
        return data
    return item


def _ensure_founder(
    db_hndlr: Database, founder_profile: Dict[str, Any]
) -> Optional[Founder]:
    founder_name = founder_profile.get("name")
    if not founder_name:
        return None

    founders = db_hndlr.retrieve_items(Founder)
    existing_founder = next(
        (founder for founder in founders if founder.name == founder_name), None
    )
    if existing_founder is not None:
        logger.warning(
            "Founder profile already exists in database, skipping profile setup."
        )
        return existing_founder

    founder = Founder(
        name=founder_name,
        profile={key: value for key, value in founder_profile.items() if key != "name"},
    )
    db_hndlr.add_item(founder)
    logger.info("Founder profile %s added to database.", founder_name)
    return founder


def run_daily_pipeline(
    founder_profile: Optional[Dict[str, Any]] = None, args=None
) -> Dict[str, Any]:
    """Run ingestion, filtering, enrichment, opportunity generation, and scoring."""

    founder_profile = founder_profile or {}

    cfg = load_config()
    is_mock = getattr(args, "dry_run", False)
    database_file = (
        os.path.join(".tmp", getattr(args, "database_file"))
        if is_mock
        else getattr(args, "database_file")
    )

    _ensure_parent_dir(database_file)
    db_hndlr = Database(
        database_file,
        recreate_on_schema_change=getattr(args, "recreate_on_schema_change", False),
    )
    founder = _ensure_founder(db_hndlr, founder_profile)

    max_items = 1 if is_mock else get_config_value(cfg, "ingestion.rss.max_items", 50)
    articles = []

    if getattr(args, "update_db", False):
        fetch_rss_articles(
            urls=get_config_value(cfg, "ingestion.rss.urls", []),
            max_items=max_items,
            db_hndlr=db_hndlr,
        )

    articles = db_hndlr.retrieve_items(Feed)

    filter_agent = FilterAgent(
        filter_config=get_config_value(cfg, "agents.filter"),
        db_hndlr=db_hndlr,
    )
    filter_agent.process(args=args)
    filtered_articles = [
        article
        for article in db_hndlr.retrieve_items(Feed)
        if not getattr(article, "is_noise", False)
    ]

    enrichment_agent = EnrichmentAgent(
        model=get_config_value(cfg, "agents.enrichment.model"),
        db_hndlr=db_hndlr,
    )
    enrichment_agent.process()

    scored_opportunities = []
    founder_name = founder.name if founder is not None else founder_profile.get("name")

    if getattr(args, "generate_opp", False):
        if not founder_name:
            logger.warning(
                "Skipping opportunity generation because no founder profile is available."
            )
        else:
            opportunity_agent = OpportunityAgent(
                model=get_config_value(cfg, "agents.opportunity.model"),
                db_hndlr=db_hndlr,
            )
            opportunity_agent.process(founder_name=founder_name, args=args)

            scoring_agent = ScoringAgent(
                model=get_config_value(cfg, "agents.scoring.model"),
                db_hndlr=db_hndlr,
            )
            scored_opportunities = scoring_agent.process(founder_name, args=args)

    if is_mock and not getattr(args, "keep_temp", False) and os.path.exists(".tmp"):
        try:
            os.rmdir(".tmp")
        except OSError:
            pass

    return {
        "articles": [_serialize_model(article) for article in articles],
        "filtered": [_serialize_model(article) for article in filtered_articles],
        "opportunities": scored_opportunities,
    }
