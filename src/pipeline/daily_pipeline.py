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


def normalize_founder_name(name: str) -> str:
    return (name or "").replace(" ", "_").lower()


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
) -> None:
    """Run ingestion, filtering, enrichment, opportunity generation, and scoring."""

    founder_profile = founder_profile or {}

    cfg = load_config(
        config_path=f"src/config/profiles/{normalize_founder_name(founder_profile.get('name'))}/filter.yaml"
    )
    database_file = getattr(args, "database_file")

    _ensure_parent_dir(database_file)
    db_hndlr = Database(
        database_file,
        recreate_on_schema_change=getattr(args, "recreate_on_schema_change", False),
    )
    founder = _ensure_founder(db_hndlr, founder_profile)

    max_items = getattr(args, "update_db", 0)

    if max_items > 0:
        logger.info(
            "Fetching RSS articles and updating database. Max items: %s", max_items
        )
        fetch_rss_articles(
            urls=get_config_value(cfg, "ingestion.rss.urls", []),
            max_items=max_items,
            db_hndlr=db_hndlr,
        )

    if getattr(args, "refilter", False):
        logger.info("Re-filtering articles in database.")
        filter_agent = FilterAgent(
            filter_config=get_config_value(cfg, "agents.filter"),
            db_hndlr=db_hndlr,
        )
        filter_agent.process(args=args)

        # logger.info("Enriching articles in database.")
        # enrichment_agent = EnrichmentAgent(
        #     model=get_config_value(cfg, "agents.enrichment.model"),
        #     db_hndlr=db_hndlr,
        # )
        # enrichment_agent.process()

    founder_name = founder.name if founder is not None else "Unknown"

    if getattr(args, "generate_opp", False):
        if not founder_name:
            logger.warning(
                "Skipping opportunity generation because no founder profile is available."
            )
        else:
            logger.info("Generating opportunities for founder: %s", founder_name)
            logger.info(
                f"{getattr(args, 'max_opps', 0)} opportunities will be generated."
            )
            opportunity_agent = OpportunityAgent(
                model=get_config_value(cfg, "agents.opportunity.model"),
                db_hndlr=db_hndlr,
            )
            opportunity_agent.process(founder_name=founder_name, args=args)

    if not getattr(args, "skip_score_opps", False):
        scoring_agent = ScoringAgent(
            model=get_config_value(cfg, "agents.scoring.model"),
            db_hndlr=db_hndlr,
        )
        scoring_agent.process(founder_name, args=args)
