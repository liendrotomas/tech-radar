import json
import os
import sys
from sqlmodel import Session, select

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.database.database import (
    Database,
    Feed,
    Founder,
    FounderFeed,
    Opportunity,
    Feedback,
)

SOURCE_DB = os.path.join("outputs", "tech_radar.db")
BASE_DIR = os.path.dirname(SOURCE_DB)


def dedupe_by_keys(items, key_fields):
    """Return unique items preserving first appearance order."""
    seen = set()
    unique = []
    for item in items:
        key = tuple(item.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def dump_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    temp_path = f"{path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)
    os.replace(temp_path, path)


def export_db(base_path: str = BASE_DIR, source_db: str = SOURCE_DB):
    db_hndlr = Database(source_db, True)
    with Session(db_hndlr.get_engine()) as session:

        # ---- FEEDS ----
        feeds = [f.model_dump() for f in session.exec(select(Feed)).all()]
        feeds = dedupe_by_keys(feeds, ["link"])
        dump_json(os.path.join(base_path, "feeds.json"), feeds)

        # ---- GROUP BY FOUNDER ----
        founders = [f.model_dump() for f in session.exec(select(Founder)).all()]
        founders = dedupe_by_keys(founders, ["name"])

        for founder in founders:
            fname = founder["name"]
            fpath = os.path.join(base_path, fname.replace(" ", "_").lower())
            os.makedirs(fpath, exist_ok=True)

            # founder
            dump_json(os.path.join(fpath, "founder.json"), founder)

            # opportunities
            opps = [
                o.model_dump()
                for o in session.exec(
                    select(Opportunity).where(Opportunity.founder_name == fname)
                ).all()
            ]
            if opps and all(o.get("id") is not None for o in opps):
                opps = dedupe_by_keys(opps, ["id"])
            else:
                opps = dedupe_by_keys(opps, ["founder_name", "title", "description"])

            dump_json(
                os.path.join(fpath, "opportunities.json"),
                opps,
            )

            # feedback
            opp_ids = [o.get("id") for o in opps if o.get("id") is not None]
            feedbacks = [
                f.model_dump()
                for f in session.exec(
                    select(Feedback).where(Feedback.founder_name == fname)
                ).all()
            ]
            feedbacks = [f for f in feedbacks if f.get("opportunity_id") in opp_ids]
            if feedbacks and all(f.get("id") is not None for f in feedbacks):
                feedbacks = dedupe_by_keys(feedbacks, ["id"])
            else:
                feedbacks = dedupe_by_keys(
                    feedbacks, ["opportunity_id", "label", "title", "notes"]
                )

            dump_json(
                os.path.join(fpath, "feedback.json"),
                feedbacks,
            )

            # founder feed
            founder_feeds = [
                f.model_dump()
                for f in session.exec(
                    select(FounderFeed).where(FounderFeed.founder_name == fname)
                ).all()
            ]

            dump_json(
                os.path.join(fpath, "founder_feed.json"),
                founder_feeds,
            )


if __name__ == "__main__":
    export_db()
