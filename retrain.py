from agents.learning_agent import LearningEngine
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
    # Initialize database and feedback service
    db = Database(DEFAULT_DATABASE_FILE)
    # Initialize learning engine and retrain
    load_dotenv()
    client = OpenAI()
    fs = FeedbackService(db)
    opportunities = db.retrieve_items(Opportunity)
    le = LearningEngine(embedder, fs, client=client)
    logger.info("Starting retraining process...")
    le.retrain()
    

print("🧠 retrained")

if __name__ == "__main__":
    main()