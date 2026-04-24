from sqlalchemy.orm import Session
from utils.logger import get_logger
from src.database.database import Database, Feedback, Opportunity
from sklearn.metrics.pairwise import cosine_similarity
from src.utils.ai_tools import embedder

logger = get_logger("FeedbackService")


class FeedbackService:

    def __init__(self, database_engine: Database, founder_name: str):
        self.database_engine = database_engine
        self.session_factory = Session(self.database_engine.get_engine())
        self.founder_name = founder_name

    def add_feedback(self, opportunity_id, label, notes=None):
        with self.session_factory as session:
            opp = (
                session.query(Opportunity)
                .filter(Opportunity.id == opportunity_id)
                .first()
            )
            existing_fb = (
                session.query(Feedback)
                .filter(Feedback.opportunity_id == opportunity_id)
                .first()
            )
            if not opp:
                logger.error(
                    f"Opportunity with id {opportunity_id} not found. Cannot add feedback."
                )
                return
            if existing_fb and (
                existing_fb.notes is not None or existing_fb.label is not None
            ):
                logger.warning(
                    f"opportunity_id already has feedback, overwriting notes with new input: {existing_fb.notes} -> {notes}"
                )
                logger.warning(
                    f"opportunity_id already has label, overwriting notes with new input: {existing_fb.label} -> {label}"
                )

                input_val = input("Press Y/y to confirm...")
                if input_val.lower() != "y":
                    logger.info("Aborting feedback update.")
                    return
                else:
                    # remove existing feedback popping out and updating the table id
                    session.delete(existing_fb)
                    session.commit()

                    fb = Feedback(
                        opportunity_id=opportunity_id,
                        label=label,
                        notes=notes,
                        founder_name=self.founder_name,
                    )
            else:
                fb = Feedback(
                    opportunity_id=opportunity_id,
                    label=label,
                    notes=notes,
                    founder_name=self.founder_name,
                )

            fb.title = opp.title
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

    def build_context(self, client, query_text, k=5):
        all_feedback = []
        for text in query_text:
            # dictionary to string:
            str_text = f"title: {text.get('title', '')}"
            all_feedback.extend(self.get_relevant_feedback(client, str_text, k))

        # Create tuple for (opportunity title, feedback) for liked and rejected feedback
        liked = [
            (
                f["opportunity_title"],
                f["feedback_notes"],
            )
            for f in all_feedback
            if f["feedback_label"] == "liked"
        ]
        rejected = [
            (f["opportunity_title"], f["feedback_notes"])
            for f in all_feedback
            if f["feedback_label"] == "rejected"
        ]

        return f"""
        Liked ideas (format as title: notes):
        {[f"{title}: {notes[:100]}" for title, notes in liked]}

        Rejected ideas (format as title: notes):
        {[f"{title}: {notes[:100]}" for title, notes in rejected]}
        """

    def remove_feedback_for_opportunity(self, opportunity_id):
        with self.session_factory as session:
            feedback = (
                session.query(Feedback)
                .filter(Feedback.opportunity_id == opportunity_id)
                .all()
            )
            if feedback:
                for fb in feedback:
                    session.delete(fb)
                session.commit()
                logger.info(f"Removed feedback for opportunity_id {opportunity_id}")
            else:
                logger.warning(f"No feedback found for opportunity_id {opportunity_id}")

    def get_all_feedback_with_opportunities(self):
        with self.session_factory as session:
            feedbacks = (
                session.query(Feedback)
                .where(Feedback.founder_name == self.founder_name)
                .all()
            )
            results = []
            for fb in feedbacks:
                opp = (
                    session.query(Opportunity)
                    .filter(Opportunity.id == fb.opportunity_id)
                    .first()
                )
                if opp:
                    results.append(
                        {
                            "opportunity_id": opp.id,
                            "opportunity_title": opp.title,
                            "feedback_label": fb.label,
                            "feedback_notes": fb.notes,
                            "opportunity": opp,
                        }
                    )
            return results

    def get_relevant_feedback(self, client, query_text, k=5):
        q_emb = embedder(client, query_text)[0]
        feedbacks = self.get_all_feedback_with_opportunities()

        scored = []
        for f in feedbacks:
            if f.get("feedback_notes", "") is None or f.get("feedback_notes", "") == "":
                if (
                    f.get("feedback_label", "") is None
                    or f.get("feedback_label", "") == ""
                ):
                    continue
                else:
                    emb = embedder(client, [f.get("feedback_label", "")])[0]
            else:
                emb = embedder(client, [f.get("feedback_notes", "")])[0]
            sim = cosine_similarity([q_emb], [emb])[0][0]
            scored.append((sim, f))

        scored.sort(reverse=True)
        return [f for _, f in scored[:k]]
