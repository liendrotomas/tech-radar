"""Tech Radar entrypoint and CLI."""

import argparse
import os, sys
from src.pipeline.daily_pipeline import run_daily_pipeline
from src.utils.logger import get_logger
from src.utils.report import print_report

logger = get_logger("main")

DEFAULT_DATABASE_FILE = os.path.join("outputs", "feeds.json")
DEFAULT_OUTPUT_DIR = os.path.join("outputs")


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
        "--update_db",
        action="store_true",
        default=False,
        help="Update the database with new opportunities",
    )
    parser.add_argument(
        "--filter-update-all",
        action="store_true",
        default=False,
        help="Update the filtered and enriched database with all articles instead of just new ones",
    )
    parser.add_argument(
        "--database-file",
        type=str,
        default=DEFAULT_DATABASE_FILE,
        help="Path to the feeds database file",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default=DEFAULT_OUTPUT_DIR,
        help="Path to the opportunities output file",
    )

    args = parser.parse_args()

    logger.info("Starting Tech Radar daily pipeline")
    setup_profile = {}
    try:
        import json

        if args.founder.endswith(".json"):
            founder_filename = args.founder
        else:
            founder_filename = args.founder + ".json"

        with open(
            os.path.join("src", "config", "profiles", founder_filename), "r"
        ) as f:
            setup_profile = json.load(f)

        args.output_file = os.path.join(
            DEFAULT_OUTPUT_DIR,
            f"{setup_profile.get('name', 'founder')}",
            "opportunities.json",
        )

    except Exception as exc:
        logger.warning("Could not parse founder profile, using empty profile: %s", exc)
    results = run_daily_pipeline(founder_profile=setup_profile, args=args)
    logger.info(
        "Pipeline complete, opportunities=%d", len(results.get("opportunities", []))
    )
    print_report(results)

    if args.dry_run:
        print("Dry run output:", results)


if __name__ == "__main__":
    cli()
