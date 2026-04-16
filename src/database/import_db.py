import json
import os
import sys
from typing import List
from sqlmodel import Session, select
from datetime import datetime

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.database.database import Database, Feed, Founder, Opportunity, Feedback

SOURCE_DB = os.path.join("outputs", "tech_radar.db")
BASE_DIR = os.path.dirname(SOURCE_DB)


# ---------- HELPERS ----------
def load_json(path):
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_datetime(val):
    if not val:
        return None
    if isinstance(val, datetime):
        return val
    return datetime.fromisoformat(val)


# ---------- UPSERT HELPERS ----------
def upsert_feed(session, item):
    existing = session.exec(select(Feed).where(Feed.link == item["link"])).first()

    if existing:
        return

    item.pop("id", None)
    session.add(Feed(**item))


def insert_generic(session, model, item):
    item.pop("id", None)
    session.add(model(**item))


# ---------- MAIN ----------
def import_db(
    base_path=BASE_DIR, source_db=SOURCE_DB, founder_name: List[str] = ["tomas_liendro"]
):
    db_hndlr = Database(source_db, True)
    with Session(db_hndlr.get_engine()) as session:

        # ---- FEEDS (GLOBAL) ----
        feeds = load_json(os.path.join(base_path, "feeds.json"))
        for f in feeds:
            upsert_feed(session, f)

        # ---- FOUNDERS (PER PROFILE) ----
        if founder_name:
            for name in founder_name:
                founders_dir = os.path.join(base_path, name.replace(" ", "_").lower())

                if os.path.exists(founders_dir):

                    # founder.json
                    founder_data = load_json(os.path.join(founders_dir, "founder.json"))
                    if founder_data:
                        insert_generic(session, Founder, founder_data)

                    # opportunities.json
                    opps = load_json(os.path.join(founders_dir, "opportunities.json"))
                    for o in opps:
                        o["created_at"] = parse_datetime(o.get("created_at"))
                        insert_generic(session, Opportunity, o)

                    # feedback.json
                    feedbacks = load_json(os.path.join(founders_dir, "feedback.json"))
                    for fb in feedbacks:
                        insert_generic(session, Feedback, fb)

        session.commit()


if __name__ == "__main__":
    import_db()
