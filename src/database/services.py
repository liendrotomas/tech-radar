from sqlalchemy.orm import Session
from utils.logger import get_logger
from src.database.database import Database, Feedback

logger = get_logger("FeedbackService")


class FeedbackService:

    def __init__(self, database_engine: Database):
        self.database_engine = database_engine
        self.session_factory = Session(self.database_engine.get_engine())

    def add_feedback(self, opportunity_id, label, notes=None):
        with self.session_factory as session:
            fb = Feedback(opportunity_id=opportunity_id, label=label, notes=notes)
            if fb.notes is not None or fb.label is not None:
                logger.warning(
                    f"opportunity_id already has feedback, overwriting notes with new input: {fb.notes} -> {notes}"
                )
                logger.warning(
                    f"opportunity_id already has label, overwriting notes with new input: {fb.label} -> {label}"
                )

                input_val = input("Press Y/y to confirm...")
                if input_val.lower() != "y":
                    logger.info("Aborting feedback update.")
                    return
            session.add(fb)
            session.commit()

    def get_by_label(self, label, limit=20):
        with self.session_factory as session:
            return (
                session.query(Feedback)
                .filter(Feedback.label == label)
                .limit(limit)
                .all()
            )

    def build_context(self):
        liked = self.get_by_label("liked")
        rejected = self.get_by_label("rejected")

        return f"""
        Liked ideas:
        {[f.notes for f in liked if f.notes]}

        Rejected ideas:
        {[f.notes for f in rejected if f.notes]}
        """
