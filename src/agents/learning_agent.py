import os

from sklearn.linear_model import LogisticRegression
import joblib


class LearningEngine:
    def __init__(self, embedder, fs, client):
        self.embedder = embedder
        self.fs = fs
        self.client = client

    def retrain(self, founder_name=None):
        # Fetch all feedback and associated opportunities
        feedbacks = self.fs.get_all_feedback_with_opportunities()

        # Prepare training data
        X = []
        y = []
        for fb in feedbacks:
            opportunity = fb.get("opportunity", None)
            if opportunity is None:
                continue  # Skip if no associated opportunity

            # Create a combined text representation of the opportunity
            text_representation = f"{opportunity.title} {opportunity.description}"
            X.append(text_representation)
            y.append(fb.get("feedback_label", None))

        if not X:
            print("No feedback data available for retraining.")
            return

        # Generate embeddings for the training data
        embeddings = self.embedder(self.client, X)

        # Train a simple classifier (e.g., logistic regression)
        clf = LogisticRegression()
        clf.fit(embeddings, y)

        # Save the trained model (this is a placeholder, implement as needed)
        os.makedirs(
            os.path.join("outputs", founder_name.replace(" ", "_").lower()),
            exist_ok=True,
        )
        joblib.dump(
            clf,
            os.path.join(
                "outputs",
                founder_name.replace(" ", "_").lower(),
                "feedback_classifier.joblib",
            ),
        )

    def predict(self, opportunity, founder_name=None):
        if founder_name:
            text = f"{opportunity.title} {opportunity.description}"
            embedding = self.embedder(self.client, [text])
            try:
                clf = joblib.load(
                    os.path.join(
                        "outputs",
                        founder_name.replace(" ", "_").lower(),
                        "feedback_classifier.joblib",
                    )
                )
            except FileNotFoundError:
                print("Trained model not found. Please run retrain() first.")
                return {"liked": 0.0, "rejected": 0.0, "explore": 0.0}

            probs = clf.predict_proba(embedding)[0]
            classes = clf.classes_

            return dict(zip(classes, probs))
        else:
            return None
