"""Remove noise-tagged founder feeds from the database."""

import argparse
import os
import sys
from typing import Tuple

from sqlmodel import Session, select

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from src.database.database import Database, Feed, FounderFeed
from src.database.export_db import export_db
from src.database.import_db import import_db

SOURCE_DB = os.path.join("outputs", "tech_radar.db")


def remove_noise_entries(
    founder_name: str, source_db: str = SOURCE_DB
) -> Tuple[int, int]:
    """Remove noise-tagged founder feeds and orphan feed rows.

    Returns:
        Tuple[removed_founder_feed_count, removed_feed_count]
    """
    database = Database(source_db)
    removed_founder_feed_count = 0
    removed_feed_count = 0

    with Session(database.get_engine()) as session:
        noise_rows = session.exec(
            select(FounderFeed).where(
                FounderFeed.founder_name == founder_name,
                FounderFeed.is_noise.is_(True),
            )
        ).all()

        for row in noise_rows:
            session.delete(row)
            removed_founder_feed_count += 1

        # Keep only feeds that are still referenced by founder_feed.
        referenced_feed_ids = set(session.exec(select(FounderFeed.feed_id)).all())
        feed_rows = session.exec(select(Feed)).all()
        for feed in feed_rows:
            if feed.id not in referenced_feed_ids:
                session.delete(feed)
                removed_feed_count += 1

        session.commit()

    return removed_founder_feed_count, removed_feed_count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove noise-tagged founder feeds from outputs/tech_radar.db"
    )
    parser.add_argument(
        "--founder-name",
        default="Tomas Liendro",
        help="Founder name as stored in DB, e.g. 'Tomas Liendro'",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    founder_name = args.founder_name

    if 1:
        import_db(founder_name=founder_name)

    removed_founder_feed_count, removed_feed_count = remove_noise_entries(
        founder_name=founder_name,
        source_db=SOURCE_DB,
    )
    # Export database after cleanup to JSON files for backup and easier inspection.
    export_db(source_db=SOURCE_DB)
    print(
        f"Removed {removed_founder_feed_count} noise founder_feed rows and {removed_feed_count} orphan feed rows for founder '{founder_name}'."
    )


if __name__ == "__main__":
    main()
