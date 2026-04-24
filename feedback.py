import argparse
import os


from src.database.import_db import import_db
from src.database.export_db import export_db
from src.database.services import FeedbackService
from src.database.database import Database, Feedback, Opportunity
from src.utils.logger import get_logger

DEFAULT_DATABASE_FILE = os.path.join("outputs", "tech_radar.db")

logger = get_logger("cli")
label_map = {"l": "liked", "r": "rejected", "e": "explore"}


def review(db_hndlr: Database, fs: FeedbackService):
    with db_hndlr.get_session() as session:
        opps = (
            session.query(Opportunity)
            .where(Opportunity.founder_name == fs.founder_name)
            .outerjoin(Feedback, Opportunity.id == Feedback.opportunity_id)
            .filter(Feedback.id == None)
            .all()
        )
    logger.info(
        f"Found {len(opps)} opportunities without feedback for founder '{fs.founder_name}'."
    )
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
    parser.add_argument(
        "--founder",
        type=str,
        default=None,
        help="Name of the founder providing feedback",
    )

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("review")
    remove_fb = sub.add_parser("remove-feedback")
    remove_fb.add_argument(
        "opportunity_id", type=int, help="ID of the opportunity to remove feedback for"
    )

    fb = sub.add_parser("feedback")
    fb.add_argument("opportunity_id", default=None, type=int, nargs="?")
    fb.add_argument(
        "label",
        default=None,
        type=str,
        nargs="?",
    )
    fb.add_argument("notes", default=None, type=str, nargs="?")

    args = parser.parse_args()
    # Load database and feedback service
    import_db(os.path.dirname(args.database_file), args.database_file)
    db = Database(args.database_file)
    fs = FeedbackService(db, founder_name=args.founder)

    if args.command == "review":
        review(db, fs)
    elif args.command == "feedback":
        label_mapped = label_map.get(args.label)
        fs.add_feedback(args.opportunity_id, label_mapped, args.notes)
    elif args.command == "remove-feedback":
        fs.remove_feedback_for_opportunity(args.opportunity_id)
    export_db(os.path.dirname(args.database_file), args.database_file)
    print("✅ feedback saved")


if __name__ == "__main__":
    main()
