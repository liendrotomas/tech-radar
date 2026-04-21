import argparse

from agents.learning_agent import LearningEngine
from database.import_db import import_db
from src.database.database import Database, Opportunity
import os
from dotenv import load_dotenv
from openai import OpenAI
from utils.ai_tools import embedder
from src.database.services import FeedbackService
from src.utils.logger import get_logger

DEFAULT_DATABASE_FILE = os.path.join("outputs", "tech_radar.db")
logger = get_logger("retrain")


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
        default="Sebastian Calvera",
        help="Name of the founder providing feedback",
    )
    args = parser.parse_args()

    # Initialize database and feedback service
    import_db(os.path.dirname(args.database_file), args.database_file)
    db = Database(args.database_file)
    fs = FeedbackService(db, args.founder)
    # Initialize learning engine and retrain
    load_dotenv()
    le = LearningEngine(embedder, fs, client=OpenAI())
    logger.info("Starting retraining process...")
    le.retrain(args.founder)
    print(f"🧠 retrained for founder '{args.founder}'")


if __name__ == "__main__":
    main()
