"""Which anchor items are worded most like a new question? TF-IDF cosine similarity."""

from __future__ import annotations


def item_text(item: dict) -> str:
    # options are left out: shared answer words ("a great deal", "agree") would
    # make every item on the same answer scale look alike
    return f"{item['title']} {item['question']}"


def nearest(question: str, items: list[dict], k: int) -> list[tuple[dict, float]]:
    """The ``k`` items most similar to ``question``, best first, with cosine similarity."""
    from sklearn.feature_extraction.text import TfidfVectorizer

    vec = TfidfVectorizer(stop_words="english", sublinear_tf=True)
    docs = vec.fit_transform([item_text(it) for it in items])
    sims = (docs @ vec.transform([question]).T).toarray().ravel()  # rows are L2-normalised
    order = sorted(range(len(items)), key=lambda i: (-sims[i], items[i]["code"]))[:k]
    return [(items[i], float(sims[i])) for i in order]
