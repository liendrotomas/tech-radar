import json
import os
import sys
from typing import Any, Callable, List, Optional
from sqlmodel import Session, select
from datetime import datetime

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
def normalize_founder_name(name: str) -> str:
    return (name or "").replace(" ", "_").lower()


def build_key(item: dict, fields: List[str]) -> tuple:
    return tuple(item.get(field) for field in fields)


def upsert_by_fields(
    session: Session,
    model,
    item: dict,
    match_fields: List[str],
):
    stmt = select(model)
    for field in match_fields:
        stmt = stmt.where(getattr(model, field) == item.get(field))

    existing = session.exec(stmt).first()
    if existing:
        for key, value in item.items():
            if key != "id":
                setattr(existing, key, value)
        return

    session.add(model(**item))


def sync_model_records(
    session: Session,
    model,
    items: List[dict],
    match_fields: List[str],
    transform: Optional[Callable[[dict], dict]] = None,
    scope_filter: Optional[Callable[[Any], bool]] = None,
):
    normalized_items = []
    for item in items:
        data = dict(item)
        if transform is not None:
            data = transform(data)
        normalized_items.append(data)

    target_keys = {
        build_key(item, match_fields)
        for item in normalized_items
        if all(item.get(field) is not None for field in match_fields)
    }

    query = select(model)
    existing_rows = session.exec(query).all()
    if scope_filter is not None:
        existing_rows = [row for row in existing_rows if scope_filter(row)]

    for row in existing_rows:
        row_key = tuple(getattr(row, field) for field in match_fields)
        if row_key not in target_keys:
            session.delete(row)

    for item in normalized_items:
        upsert_by_fields(session, model, item, match_fields)


def transform_opportunity(item: dict) -> dict:
    data = dict(item)
    data["created_at"] = parse_datetime(data.get("created_at"))
    return data


# ---------- MAIN ----------
def import_db(
    base_path=BASE_DIR,
    source_db=SOURCE_DB,
    founder_name: Optional[List[str]] = None,
):
    db_hndlr = Database(source_db)
    with Session(db_hndlr.get_engine()) as session:

        # ---- FEEDS (GLOBAL) ----
        feeds = load_json(os.path.join(base_path, "feeds.json"))
        sync_model_records(
            session=session,
            model=Feed,
            items=feeds,
            match_fields=["link"],
        )

        # ---- FOUNDERS (PER PROFILE) ----
        if isinstance(founder_name, str):
            founder_names = [founder_name]
        else:
            # founder names are derived from subdirectories in the base path
            founder_names = [
                d
                for d in os.listdir(base_path)
                if os.path.isdir(os.path.join(base_path, d))
            ]
        normalized_founder_names = {
            normalize_founder_name(name) for name in founder_names
        }

        founders_payload = []
        opportunities_payload = []
        feedback_payload = []
        founder_feed_payload = []

        for name in founder_names:
            founders_dir = os.path.join(base_path, normalize_founder_name(name))

            if os.path.exists(founders_dir):

                # founder.json
                founder_data = load_json(os.path.join(founders_dir, "founder.json"))
                if founder_data:
                    founders_payload.append(founder_data)

                    # opportunities.json
                    opps = load_json(os.path.join(founders_dir, "opportunities.json"))
                    opportunities_payload.extend(opps)

                    # feedback.json
                    feedbacks = load_json(os.path.join(founders_dir, "feedback.json"))
                    feedback_payload.extend(feedbacks)

                    # founder_feed.json
                    founder_feed = load_json(
                        os.path.join(founders_dir, "founder_feed.json")
                    )
                    founder_feed_payload.extend(founder_feed)

        sync_model_records(
            session=session,
            model=Founder,
            items=founders_payload,
            match_fields=["name"],
            scope_filter=lambda row: normalize_founder_name(getattr(row, "name", ""))
            in normalized_founder_names,
        )

        sync_model_records(
            session=session,
            model=Opportunity,
            items=opportunities_payload,
            match_fields=(
                ["id"]
                if all(item.get("id") is not None for item in opportunities_payload)
                else ["founder_name", "title"]
            ),
            transform=transform_opportunity,
            scope_filter=lambda row: normalize_founder_name(
                getattr(row, "founder_name", "")
            )
            in normalized_founder_names,
        )

        scoped_opportunity_ids = {
            opp.id
            for opp in session.exec(select(Opportunity)).all()
            if (
                opp.id is not None
                and normalize_founder_name(getattr(opp, "founder_name", ""))
                in normalized_founder_names
            )
        }

        sync_model_records(
            session=session,
            model=Feedback,
            items=feedback_payload,
            match_fields=(
                ["id"]
                if all(item.get("id") is not None for item in feedback_payload)
                else ["opportunity_id", "label", "title"]
            ),
            scope_filter=lambda row: getattr(row, "opportunity_id", None)
            in scoped_opportunity_ids,
        )

        sync_model_records(
            session=session,
            model=FounderFeed,
            items=founder_feed_payload,
            match_fields=["feed_id", "founder_name"],
            scope_filter=lambda row: normalize_founder_name(
                getattr(row, "founder_name", "")
            )
            in normalized_founder_names,
        )

        session.commit()


if __name__ == "__main__":
    import_db()
