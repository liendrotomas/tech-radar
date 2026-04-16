"""Tech Radar entrypoint and CLI."""

import argparse
import json
import os

from src.database.tools import import_from_csv

from src.database.database import Database, Feed, Feedback, Founder, Opportunity
from src.database.import_db import import_db
from src.database.export_db import export_db

from src.pipeline.daily_pipeline import run_daily_pipeline
from src.utils.logger import get_logger
from src.utils.report import print_report

logger = get_logger("main")

DEFAULT_DATABASE_FILE = os.path.join("outputs", "tech_radar.db")


def _remove_opportunities_for_founder(db_hndlr: Database, founder_name: str) -> None:
    opportunities = db_hndlr.retrieve_items(Opportunity)
    for opp in opportunities:
        if opp.founder_name == founder_name:
            db_hndlr.remove_item(opp)


def _clear_database(args):
    if getattr(args, "clear_feeds", False):
        logger.warning("Clearing feeds table in database.")
        db_hndlr = Database(DEFAULT_DATABASE_FILE)
        db_hndlr.clear_items(Feed)
    if getattr(args, "clear_feedback", False):
        logger.warning("Clearing feedback table in database.")
        db_hndlr = Database(DEFAULT_DATABASE_FILE)
        db_hndlr.clear_items(Feedback)
    if getattr(args, "clear_opportunities", False):
        logger.warning("Clearing opportunities table in database.")
        db_hndlr = Database(DEFAULT_DATABASE_FILE)
        db_hndlr.clear_items(Opportunity)
    if getattr(args, "clear_founder_opps", None):
        founder_name = args.clear_founder_opps
        logger.warning(
            f"Clearing opportunities for founder {founder_name} in database."
        )
        db_hndlr = Database(DEFAULT_DATABASE_FILE)
        _remove_opportunities_for_founder(db_hndlr, founder_name)
    if getattr(args, "remove_founder", None):
        founder_name = args.remove_founder
        logger.warning(
            f"Removing founder {founder_name} and their opportunities from database."
        )
        db_hndlr = Database(DEFAULT_DATABASE_FILE)
        retreived_founders = db_hndlr.retrieve_items(Founder)
        for founder in retreived_founders:
            if founder.name == founder_name:
                db_hndlr.remove_item(founder)
        _remove_opportunities_for_founder(db_hndlr, founder_name)


def _load_founder_profile(founder_arg: str) -> dict:
    founder_filename = (
        founder_arg if founder_arg.endswith(".json") else f"{founder_arg}.json"
    )
    founder_path = os.path.join("src", "config", "profiles", founder_filename)

    with open(founder_path, "r", encoding="utf-8") as founder_file:
        return json.load(founder_file)


def cli() -> None:
    parser = argparse.ArgumentParser(description="Tech Radar AI pipeline runner")
    parser.add_argument(
        "--dry-run", action="store_true", default=False, help="Run without persistence"
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        default=False,
        help="Keep temporary files after dry run",
    )
    parser.add_argument(
        "--founder", type=str, default=None, help="Founder profile JSON string"
    )
    parser.add_argument(
        "--update-db",
        default=0,
        type=int,
        help="Fetch RSS articles and update database before processing (provide max items to fetch)",
    )
    parser.add_argument(
        "--refilter",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Re-filter articles in the database",
    )
    parser.add_argument(
        "--database-file",
        type=str,
        default=DEFAULT_DATABASE_FILE,
        help="Path to the feeds database file",
    )
    parser.add_argument(
        "--recreate-on-schema-change",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Rebuild drifted tables during development; this can delete table data",
    )
    parser.add_argument(
        "--generate-opp",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Generate opportunities from enriched articles",
    )
    parser.add_argument(
        "--max-opps", type=int, default=10, help="Max opportunities to generate"
    )
    parser.add_argument(
        "--skip-score-opps",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Skip scoring opportunities using the scoring agent",
    )
    parser.add_argument(
        "--update-scores",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Clear old and update opportunity scores",
    )

    # Create tags for clearing the database during development
    parser.add_argument(
        "--clear-feeds",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Clear feeds table in the database",
    )
    parser.add_argument(
        "--clear-feedback",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Clear feedback table in the database",
    )
    parser.add_argument(
        "--clear-opportunities",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Clear opportunities table in the database",
    )
    # Clear specific founder opportunities
    parser.add_argument(
        "--clear-founder-opps",
        type=str,
        default=None,
        help="Clear opportunities for a specific founder (provide founder name)",
    )
    # Remove founder from database
    parser.add_argument(
        "--remove-founder",
        type=str,
        default=None,
        help="Remove a founder and their opportunities from the database (provide founder name)",
    )
    parser.add_argument(
        "--feed-from-csv",
        type=str,
        default=None,  # "outputs/legacy/database_notion.csv",
        help="Import feed data from a CSV file (provide file path)",
    )

    args = parser.parse_args()
    BASE_DIR = os.path.dirname(getattr(args, "database_file", DEFAULT_DATABASE_FILE))

    logger.info("Starting Tech Radar daily pipeline")
    _clear_database(args)
    if args.feed_from_csv:
        import_from_csv(args.feed_from_csv, args)

    setup_profile = {}
    if args.founder:
        setup_profile = _load_founder_profile(args.founder)
    else:
        raise Exception(
            "Failed to load founder profile. Please check the provided founder profile."
        )

    # Import existing data from database to be enriched and processed in the pipeline
    logger.info(
        f"Importing existing database entries for processing {getattr(args, 'database_file', '')}"
    )
    import_db(
        base_path=BASE_DIR,
        source_db=args.database_file,
        founder_name=[setup_profile.get("name", "")],
    )
    run_daily_pipeline(founder_profile=setup_profile, args=args)
    logger.info("Pipeline complete.")
    # Export the updated database after processing
    logger.info(
        f"Exporting updated database entries to {getattr(args, 'database_file', '')}"
    )
    export_db(base_path=BASE_DIR, source_db=args.database_file)


if __name__ == "__main__":
    cli()
