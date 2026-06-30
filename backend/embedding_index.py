"""Vector search + TF-IDF fallback.

When real embeddings exist (Flash or local CPU), retrieve by cosine via FAISS
(if installed) or NumPy. When no embedding model is available, fall back to a
self-contained TF-IDF retriever (scikit-learn) so the demo still returns
semantically-reasonable matches with zero heavy dependencies.
"""
from __future__ import annotations

import numpy as np

try:
    import faiss

    FAISS_AVAILABLE = True
except Exception:  # noqa: BLE001
    FAISS_AVAILABLE = False


def vector_search(
    corpus_emb: np.ndarray, query_emb: np.ndarray, top_k: int
) -> list[tuple[int, float]]:
    """Cosine top-k. Embeddings are expected L2-normalized (dot == cosine)."""
    corpus_emb = np.ascontiguousarray(corpus_emb, dtype=np.float32)
    q = np.ascontiguousarray(query_emb.reshape(1, -1), dtype=np.float32)
    k = min(top_k, corpus_emb.shape[0])

    if FAISS_AVAILABLE:
        index = faiss.IndexFlatIP(corpus_emb.shape[1])  # inner product = cosine
        index.add(corpus_emb)
        scores, idxs = index.search(q, k)
        return [(int(i), float(s)) for i, s in zip(idxs[0], scores[0]) if i >= 0]

    sims = (corpus_emb @ q[0]).astype(float)
    top = np.argsort(-sims)[:k]
    return [(int(i), float(sims[i])) for i in top]


def tfidf_search(
    corpus_texts: list[str], query_text: str, top_k: int
) -> list[tuple[int, float]]:
    """Lightweight lexical/semantic-ish retrieval, no embedding model needed."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import linear_kernel

    if not corpus_texts:
        return []
    vectorizer = TfidfVectorizer(
        stop_words="english", max_features=40000, ngram_range=(1, 2)
    )
    matrix = vectorizer.fit_transform(corpus_texts)
    q_vec = vectorizer.transform([query_text])
    sims = linear_kernel(q_vec, matrix).ravel()
    k = min(top_k, len(corpus_texts))
    top = np.argsort(-sims)[:k]
    return [(int(i), float(sims[i])) for i in top]
