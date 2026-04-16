import json
import os
import sys
from sqlmodel import Session, select

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from src.database.database import Database, Feed, Founder, Opportunity, Feedback

SOURCE_DB = os.path.join("outputs", "tech_radar.db")
BASE_DIR = os.path.dirname(SOURCE_DB)


def dump_json(path, data):
    # Clear existing file and write new data
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def export_db(base_path: str = BASE_DIR, source_db: str = SOURCE_DB):
    db_hndlr = Database(source_db, True)
    with Session(db_hndlr.get_engine()) as session:

        # ---- FEEDS ----
        feeds = session.exec(select(Feed)).all()
        dump_json(
            os.path.join(base_path, "feeds.json"), [f.model_dump() for f in feeds]
        )

        # ---- GROUP BY FOUNDER ----
        founders = session.exec(select(Founder)).all()

        for founder in founders:
            fname = founder.name
            fpath = os.path.join(base_path, fname.replace(" ", "_").lower())
            os.makedirs(fpath, exist_ok=True)

            # founder
            dump_json(os.path.join(fpath, "founder.json"), founder.model_dump())

            # opportunities
            opps = session.exec(
                select(Opportunity).where(Opportunity.founder_name == fname)
            ).all()

            dump_json(
                os.path.join(fpath, "opportunities.json"),
                [o.model_dump() for o in opps],
            )

            # feedback
            feedbacks = session.exec(select(Feedback)).all()
            feedbacks = [
                f for f in feedbacks if any(o.id == f.opportunity_id for o in opps)
            ]

            dump_json(
                os.path.join(fpath, "feedback.json"),
                [f.model_dump() for f in feedbacks],
            )


if __name__ == "__main__":
    export_db()
