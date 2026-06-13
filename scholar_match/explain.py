"""Use Claude to explain *why* two scholars are a good match.

Cosine similarity tells you a pair is close; it doesn't say what they share.
This step asks Claude for a short, human-readable read on each top match:
shared themes, a one-line summary, and a concrete collaboration idea.

`anthropic` and `pydantic` are imported lazily inside the functions so the rest
of the pipeline (fetch / profiles / match / report) runs without them installed.
"""

from __future__ import annotations

import json

from . import config


def _match_schema():
    """Build the structured-output model. Imported lazily (needs pydantic)."""
    from pydantic import BaseModel, Field

    class MatchExplanation(BaseModel):
        shared_themes: list[str] = Field(
            description="Specific research topics/methods the two scholars share."
        )
        summary: str = Field(
            description="One or two sentences on why they'd connect well."
        )
        collaboration_idea: str = Field(
            description="A concrete project or paper they could pursue together."
        )

    return MatchExplanation


def _profile_blurb(profile: dict) -> str:
    titles = "; ".join(profile["titles"][:8])
    concepts = ", ".join(profile["top_concepts"])
    return f"Name: {profile['name']}\nAreas: {concepts}\nSelected work: {titles}"


def explain_pair(client, schema, a: dict, b: dict, similarity: float) -> dict:
    prompt = (
        "Two University of Wisconsin-Madison scholars work in AI/ML/statistics. "
        "A similarity model scored their research overlap at "
        f"{similarity:.2f} (0-1). Explain the match for an academic "
        "networking tool: what they actually share, and a concrete way they "
        "could collaborate. Be specific and grounded in the work listed.\n\n"
        f"SCHOLAR A\n{_profile_blurb(a)}\n\n"
        f"SCHOLAR B\n{_profile_blurb(b)}"
    )
    response = client.messages.parse(
        model=config.CLAUDE_MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
        output_format=schema,
    )
    return response.parsed_output.model_dump()


def explain_matches(
    matches: list[dict],
    profiles: list[dict],
    top_k: int = 2,
    max_authors: int | None = None,
) -> list[dict]:
    """Add LLM explanations to the top `top_k` matches of each author.

    Args:
        top_k: how many of each author's matches to explain (cost control).
        max_authors: only explain matches for the first N authors (cost control).
    """
    import anthropic

    client = anthropic.Anthropic()
    schema = _match_schema()
    by_id = {p["author_id"]: p for p in profiles}

    authors = matches[:max_authors] if max_authors else matches
    for rec in authors:
        a = by_id.get(rec["author_id"])
        if a is None:
            continue
        for m in rec["matches"][:top_k]:
            b = by_id.get(m["author_id"])
            if b is None:
                continue
            m["explanation"] = explain_pair(client, schema, a, b, m["similarity"])
            print(f"  {rec['name']}  <->  {m['name']}  ({m['similarity']})")
    return matches


def explain_and_save(
    top_k: int = 2,
    max_authors: int | None = 25,
    path=config.EXPLAINED_PATH,
) -> list[dict]:
    matches = json.loads(config.MATCHES_PATH.read_text())
    profiles = json.loads(config.PROFILES_PATH.read_text())
    explained = explain_matches(
        matches, profiles, top_k=top_k, max_authors=max_authors
    )
    path.write_text(json.dumps(explained, indent=2))
    print(f"Explained matches -> {path}")
    return explained
