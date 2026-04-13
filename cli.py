import argparse
import os
from src.database.services import FeedbackService
from src.database.database import Database, Feedback, Opportunity
from src.utils.logger import get_logger

DEFAULT_DATABASE_FILE = os.path.join("outputs", "tech_radar.db")

logger = get_logger("cli")


def review(db_hndlr: Database, fs: FeedbackService):
    with db_hndlr.get_session() as session:
        opps = (
            session.query(Opportunity)
            .outerjoin(Feedback, Opportunity.id == Feedback.opportunity_id)
            .filter(Feedback.id == None)
            .limit(20)
            .all()
        )
    logger.info(f"Found {len(opps)} opportunities without feedback.")
    for o in opps:
        print("\n" + "=" * 50)
        print(f"[{o.id}] {o.title}")
        print(o.description[:500] or o.description)

        action = (
            input("\n(l)ike / (r)eject / (e)xplore / (s)kip / (q)uit: ").strip().lower()
        )

        if action == "q":
            break
        elif action == "s":
            continue

        label_map = {"l": "liked", "r": "rejected", "e": "explore"}

        label = label_map.get(action)

        if label:
            notes = input("notes (optional): ")
            fs.add_feedback(o.id, label, notes)
            print("✅ saved")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--database-file",
        type=str,
        default=DEFAULT_DATABASE_FILE,
        help="Path to the feeds database file",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("review")

    fb = sub.add_parser("feedback")
    fb.add_argument("opportunity_id", default=None, type=int, nargs="?")
    fb.add_argument(
        "label",
        default=None,
        type=str,
        choices=["liked", "neutral", "rejected"],
        nargs="?",
    )
    fb.add_argument("notes", default=None, type=str, nargs="?")

    args = parser.parse_args()

    db = Database(args.database_file)
    fs = FeedbackService(db)

    if args.command == "review":
        review(db, fs)
    elif args.command == "feedback":
        fs.add_feedback(args.opportunity_id, args.label, args.notes)
    print("✅ feedback saved")


if __name__ == "__main__":
    main()
