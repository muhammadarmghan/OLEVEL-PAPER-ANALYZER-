"""Layered topic classifier: keywords + TF-IDF similarity + (optional) trained model."""
import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity


def _softmax(values: np.ndarray, temperature: float) -> np.ndarray:
    z = values * temperature
    z = z - z.max()
    e = np.exp(z)
    return e / e.sum()


class TopicClassifier:
    """topics = [{'id': 7, 'text': 'title + description + objectives', 'keywords': {'force': 1.0}}]"""

    def __init__(self, topics, weights=(0.5, 0.3, 0.2), temperature=10.0):
        self.topics = topics
        self.ids = [t["id"] for t in topics]
        self.w_model, self.w_tfidf, self.w_kw = weights
        self.temperature = temperature
        self.model = None
        self._fit_vectorizer([t["text"] for t in topics])

    def _fit_vectorizer(self, extra_texts):
        corpus = [t["text"] for t in self.topics] + list(extra_texts)
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        self.vectorizer.fit(corpus)
        self.topic_matrix = self.vectorizer.transform([t["text"] for t in self.topics])

    def _keyword_vector(self, text):
        scores = np.zeros(len(self.topics))
        for i, topic in enumerate(self.topics):
            for kw, weight in topic["keywords"].items():
                if re.search(rf"\b{re.escape(kw)}", text, re.IGNORECASE):
                    scores[i] += weight
        scores = np.minimum(scores / 2.0, 1.0)          # two keyword hits = full score
        return scores / scores.sum() if scores.sum() > 0 else scores

    def _tfidf_vector(self, text):
        sims = cosine_similarity(self.vectorizer.transform([text]), self.topic_matrix)[0]
        return _softmax(sims, self.temperature) if sims.max() > 0 else np.zeros(len(self.topics))

    def _model_vector(self, text):
        probs = self.model.predict_proba(self.vectorizer.transform([text]))[0]
        full = np.zeros(len(self.topics))
        for cls, p in zip(self.model.classes_, probs):
            full[self.ids.index(cls)] = p
        return full

    def fit(self, texts, topic_ids):
        """Train on the hand-labelled gold set (needs roughly 150+ examples)."""
        self._fit_vectorizer(texts)
        self.model = LogisticRegression(max_iter=2000, C=5.0).fit(self.vectorizer.transform(texts), topic_ids)

    def predict(self, text, top_n=3):
        parts = [(self.w_kw, self._keyword_vector(text)), (self.w_tfidf, self._tfidf_vector(text))]
        if self.model is not None:
            parts.append((self.w_model, self._model_vector(text)))
        live = [(w, v) for w, v in parts if v.sum() > 0]
        if not live:
            return []
        final = sum(w * v for w, v in live) / sum(w for w, _ in live)
        method = "model" if self.model is not None else "rule"
        order = np.argsort(final)[::-1][:top_n]
        return [(self.ids[i], float(final[i]), method) for i in order if final[i] > 0]


def route(confidence: float, auto=0.70, review=0.40) -> str:
    """accept / review / flag, used to decide what goes to the review queue."""
    return "accept" if confidence >= auto else "review" if confidence >= review else "flag"
