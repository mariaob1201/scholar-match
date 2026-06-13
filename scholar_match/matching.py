"""Rank author pairs by how close their research interests are.

Primary path: sentence-transformers embeddings + cosine similarity.
Fallback: TF-IDF vectors (scikit-learn) if sentence-transformers/torch isn't
installed. Both produce L2-normalized vectors, so a dot product is cosine.
"""

from __future__ import annotations

import json

import numpy as np

from . import config


def embed(texts: list[str]) -> np.ndarray:
    """Return an (n, d) matrix of L2-normalized embeddings for `texts`."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer(config.EMBEDDING_MODEL)
        vecs = model.encode(
            texts, normalize_embeddings=True, show_progress_bar=True
        )
        return np.asarray(vecs, dtype=np.float32)
    except ImportError:
        print("sentence-transformers not available; falling back to TF-IDF.")
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(
            stop_words="english", max_features=8192, ngram_range=(1, 2)
        )
        matrix = vectorizer.fit_transform(texts).toarray().astype(np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return matrix / norms


def rank_matches(profiles: list[dict], top_k: int = 5) -> list[dict]:
    """For each author, find their `top_k` most similar peers.

    Returns one record per author with a ranked list of matches. Similarity is
    cosine in [0, 1] (or [-1, 1] for TF-IDF; in practice >= 0 here).
    """
    if len(profiles) < 2:
        raise ValueError("Need at least 2 author profiles to match.")

    vecs = embed([p["profile_text"] for p in profiles])
    sim = vecs @ vecs.T  # cosine similarity matrix
    np.fill_diagonal(sim, -np.inf)  # never match an author with themselves

    results: list[dict] = []
    for i, p in enumerate(profiles):
        order = np.argsort(sim[i])[::-1][:top_k]
        matches = [
            {
                "author_id": profiles[j]["author_id"],
                "name": profiles[j]["name"],
                "similarity": round(float(sim[i, j]), 4),
                "top_concepts": profiles[j]["top_concepts"],
            }
            for j in order
            if np.isfinite(sim[i, j])
        ]
        results.append(
            {
                "author_id": p["author_id"],
                "name": p["name"],
                "top_concepts": p["top_concepts"],
                "matches": matches,
            }
        )
    return results


def rank_and_save(
    profiles: list[dict] | None = None,
    top_k: int = 5,
    path=config.MATCHES_PATH,
) -> list[dict]:
    if profiles is None:
        profiles = json.loads(config.PROFILES_PATH.read_text())
    results = rank_matches(profiles, top_k=top_k)
    path.write_text(json.dumps(results, indent=2))
    print(f"Ranked matches for {len(results)} authors -> {path}")
    return results
