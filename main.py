"""Tech Radar entrypoint and CLI."""

import argparse
import json
import os

from src.pipeline.daily_pipeline import run_daily_pipeline
from src.utils.logger import get_logger
from src.utils.report import print_report

logger = get_logger("main")

DEFAULT_DATABASE_FILE = os.path.join("outputs", "tech_radar.db")


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
        "--dry-run", action="store_true", help="Run without persistence"
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        default=False,
        help="Keep temporary files after dry run",
    )
    parser.add_argument(
        "--founder", type=str, default="tom", help="Founder profile JSON string"
    )
    parser.add_argument(
        "--update-db",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Refresh RSS items in the database",
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
        default=False,
        help="Rebuild drifted tables during development; this can delete table data",
    )
    parser.add_argument(
        "--generate-opp",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Generate opportunities from enriched articles",
    )

    args = parser.parse_args()

    logger.info("Starting Tech Radar daily pipeline")
    setup_profile = {}
    try:
        setup_profile = _load_founder_profile(args.founder)
    except Exception as exc:
        logger.warning("Could not parse founder profile, using empty profile: %s", exc)

    results = run_daily_pipeline(founder_profile=setup_profile, args=args)
    logger.info(
        "Pipeline complete, opportunities=%d",
        len(results.get("opportunities", [])),
    )
    print_report(results)


if __name__ == "__main__":
    cli()
