"""Fetch AI-related publications affiliated with UW-Madison from OpenAlex.

OpenAlex is free and needs no API key. Passing your email (OPENALEX_MAILTO)
puts requests in the faster "polite pool".
"""

from __future__ import annotations

import json
import time
from typing import Iterator

import requests

from . import config


def _reconstruct_abstract(inverted_index: dict | None) -> str:
    """OpenAlex stores abstracts as an inverted index {word: [positions]}.

    Rebuild the original text. Returns "" when no abstract is available.
    """
    if not inverted_index:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted_index.items():
        for i in idxs:
            positions.append((i, word))
    positions.sort()
    return " ".join(word for _, word in positions)


def _params(cursor: str, per_page: int) -> dict:
    concept_filter = "|".join(config.AI_CONCEPT_IDS)  # "|" = OR within a filter
    params = {
        "filter": (
            f"authorships.institutions.id:{config.UW_MADISON_ID},"
            f"concepts.id:{concept_filter}"
        ),
        "per_page": per_page,
        "cursor": cursor,
        # Only pull the fields we actually use, to keep payloads small.
        "select": (
            "id,title,publication_year,cited_by_count,"
            "abstract_inverted_index,authorships,concepts,primary_location"
        ),
    }
    if config.OPENALEX_MAILTO:
        params["mailto"] = config.OPENALEX_MAILTO
    return params


def iter_works(
    from_year: int = 2018,
    per_page: int = 200,
    max_works: int | None = None,
) -> Iterator[dict]:
    """Yield works (publications), paging through OpenAlex with a cursor."""
    cursor = "*"
    fetched = 0
    session = requests.Session()

    while cursor:
        params = _params(cursor, per_page)
        # from_publication_date keeps the set recent (and current students in it).
        params["filter"] += f",from_publication_date:{from_year}-01-01"

        resp = session.get(f"{config.OPENALEX_BASE}/works", params=params, timeout=60)
        resp.raise_for_status()
        payload = resp.json()

        for work in payload.get("results", []):
            source = (work.get("primary_location") or {}).get("source") or {}
            yield {
                "id": work["id"],
                "title": work.get("title") or "",
                "year": work.get("publication_year"),
                "cited_by_count": work.get("cited_by_count", 0),
                "abstract": _reconstruct_abstract(work.get("abstract_inverted_index")),
                "venue": source.get("display_name", ""),
                "concepts": [
                    {"name": c["display_name"], "score": c.get("score", 0)}
                    for c in work.get("concepts", [])
                ],
                "authorships": [
                    {
                        "author_id": a["author"]["id"],
                        "name": a["author"].get("display_name", ""),
                        "is_uw": any(
                            inst.get("id") == f"https://openalex.org/{config.UW_MADISON_ID}"
                            for inst in a.get("institutions", [])
                        ),
                    }
                    for a in work.get("authorships", [])
                ],
            }
            fetched += 1
            if max_works and fetched >= max_works:
                return

        cursor = payload.get("meta", {}).get("next_cursor")
        time.sleep(0.1)  # be gentle


def fetch_and_save(
    from_year: int = 2018,
    max_works: int | None = None,
    path=config.WORKS_PATH,
) -> list[dict]:
    """Fetch works and write them to disk. Returns the list."""
    works = list(iter_works(from_year=from_year, max_works=max_works))
    path.write_text(json.dumps(works, indent=2))
    print(f"Fetched {len(works)} works -> {path}")
    return works
