"""Group works into per-author research profiles.

A "profile" is everything we know about one UW-Madison author across the
AI-related works we pulled: their papers, the concepts that recur in them, and
a single block of text we can embed.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict

from . import config


def build_profiles(
    works: list[dict],
    min_works: int = 2,
    max_works_per_author: int | None = None,
) -> list[dict]:
    """Turn a flat list of works into author profiles.

    Only authors flagged as UW-Madison-affiliated on a given work are credited
    for it, so co-authors from other institutions don't pollute the set.

    Args:
        min_works: drop authors with fewer than this many AI works. Filters out
            one-off co-authors and keeps people with a real AI/stats footprint.
        max_works_per_author: cap papers per author in the embedded text (most
            cited first), so prolific PIs don't dominate purely by volume.
    """
    by_author: dict[str, dict] = defaultdict(
        lambda: {"name": "", "works": [], "concepts": Counter()}
    )

    for w in works:
        for a in w["authorships"]:
            if not a["is_uw"]:
                continue
            entry = by_author[a["author_id"]]
            entry["name"] = a["name"] or entry["name"]
            entry["works"].append(w)
            for c in w["concepts"]:
                entry["concepts"][c["name"]] += 1

    profiles: list[dict] = []
    for author_id, entry in by_author.items():
        works_sorted = sorted(
            entry["works"], key=lambda w: w["cited_by_count"], reverse=True
        )
        if len(works_sorted) < min_works:
            continue
        text_works = (
            works_sorted[:max_works_per_author]
            if max_works_per_author
            else works_sorted
        )
        profiles.append(
            {
                "author_id": author_id,
                "name": entry["name"],
                "n_works": len(works_sorted),
                "total_citations": sum(w["cited_by_count"] for w in works_sorted),
                "top_concepts": [c for c, _ in entry["concepts"].most_common(10)],
                "titles": [w["title"] for w in works_sorted],
                "profile_text": _profile_text(entry, text_works),
            }
        )

    profiles.sort(key=lambda p: p["n_works"], reverse=True)
    return profiles


def _profile_text(entry: dict, works: list[dict]) -> str:
    """Concatenate concepts + titles + abstracts into one embeddable string."""
    parts: list[str] = []
    top_concepts = ", ".join(c for c, _ in entry["concepts"].most_common(10))
    if top_concepts:
        parts.append(f"Research areas: {top_concepts}.")
    for w in works:
        parts.append(w["title"])
        if w["abstract"]:
            parts.append(w["abstract"])
    return "\n".join(p for p in parts if p)


def build_and_save(
    works: list[dict] | None = None,
    min_works: int = 2,
    max_works_per_author: int | None = 20,
    path=config.PROFILES_PATH,
) -> list[dict]:
    if works is None:
        works = json.loads(config.WORKS_PATH.read_text())
    profiles = build_profiles(
        works, min_works=min_works, max_works_per_author=max_works_per_author
    )
    path.write_text(json.dumps(profiles, indent=2))
    print(f"Built {len(profiles)} author profiles -> {path}")
    return profiles
