import numpy as np
from openai import OpenAI


class LearningEngine:

    def __init__(self, texts: list[str], feedback_service):
        self.embed = self.embedder(texts)
        self.fs = feedback_service
        self.liked_centroid = None
        self.rejected_centroid = None

    # ---------- TRAIN (batch) ----------
    def retrain(self):
        liked = self.fs.get_by_label("liked", limit=100)
        rejected = self.fs.get_by_label("rejected", limit=100)

        liked_texts = [f.notes for f in liked if f.notes]
        rejected_texts = [f.notes for f in rejected if f.notes]

        if liked_texts:
            self.liked_centroid = self._centroid(self.embed(liked_texts))

        if rejected_texts:
            self.rejected_centroid = self._centroid(self.embed(rejected_texts))

    # ---------- SCORE ----------
    def score(self, text, base_score=0):
        emb = self.embed([text])[0]

        s = base_score

        if self.liked_centroid is not None:
            s += self._sim(emb, self.liked_centroid) * 0.5

        if self.rejected_centroid is not None:
            s -= self._sim(emb, self.rejected_centroid) * 0.7

        return s

    # ---------- UTILS ----------
    def _centroid(self, vectors):
        return np.mean(vectors, axis=0)

    def _sim(self, a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def embedder(texts: list[str]) -> list[list[float]]:
        client = OpenAI()
        res = client.embeddings.create(model="text-embedding-3-small", input=texts)
        return [e.embedding for e in res.data]
