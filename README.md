# scholar-match

Find UW-Madison scholars working on similar things in **AI / ML / statistics**,
and match them by how close their published research is.

It pulls every AI-related publication affiliated with the University of
Wisconsin–Madison from [OpenAlex](https://openalex.org), groups the papers by
author into research profiles, ranks author pairs by the similarity of their
work (embeddings + cosine), and uses **Claude** to explain each top match in
plain language — shared themes and a concrete way they could collaborate.

> The "focus on stats" is baked into the topic filter: the AI concept set
> includes *Statistics* and *Statistical learning*, so the stats-flavored ML
> crowd is captured alongside core CS/ECE AI work.

## How it works

```
OpenAlex  ──►  profiles  ──►  matching  ──►  explain
 (works)      (per author)   (cosine sim)   (Claude)
```

| Stage | File | What it does |
|-------|------|--------------|
| fetch | `scholar_match/openalex.py` | AI-related works at UW-Madison (no API key needed) |
| profiles | `scholar_match/profiles.py` | one embeddable text profile per author |
| match | `scholar_match/matching.py` | embed profiles, rank each author's nearest peers |
| explain | `scholar_match/explain.py` | Claude writes why each top pair matches |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add ANTHROPIC_API_KEY + OPENALEX_MAILTO
```

`ANTHROPIC_API_KEY` is only needed for the `explain` stage. OpenAlex needs no
key — your email just gets you into its faster "polite pool".

## Run

End to end (cap the fetch while you try it out):

```bash
python -m scholar_match.pipeline all --from-year 2020 --max-works 3000
```

Or stage by stage:

```bash
python -m scholar_match.pipeline fetch    --from-year 2020 --max-works 3000
python -m scholar_match.pipeline profiles --min-works 3
python -m scholar_match.pipeline match    --top-k 5
python -m scholar_match.pipeline explain  --max-authors 25 --top-k 2
```

Outputs land in `data/` as JSON:

- `works.json` — raw publications
- `profiles.json` — per-author profiles
- `matches.json` — ranked similar-author pairs + cosine scores
- `matches_explained.json` — the above, plus Claude's match explanations

### Example output (`matches_explained.json`)

```json
{
  "name": "Author A",
  "top_concepts": ["Machine learning", "Causal inference", "Statistics"],
  "matches": [
    {
      "name": "Author B",
      "similarity": 0.71,
      "explanation": {
        "shared_themes": ["high-dimensional inference", "semiparametric methods"],
        "summary": "Both work on statistical guarantees for ML estimators ...",
        "collaboration_idea": "A joint paper on doubly-robust estimation for ..."
      }
    }
  ]
}
```

## Design notes & honest limitations

- **Embeddings.** Defaults to `sentence-transformers` (`all-MiniLM-L6-v2`). If
  you can't install torch, it automatically falls back to TF-IDF — the pipeline
  still runs, just with shallower matching. Anthropic doesn't offer an
  embeddings endpoint, so Claude is used for the *explanation* step, not vectors.
- **"PhD students" is an approximation.** OpenAlex doesn't label career stage,
  so there's no reliable "is a PhD student" flag. Restricting to recent years
  (`--from-year`) and authors with a few papers (`--min-works`) is a proxy. For
  true student filtering you'd cross-reference a department roster.
- **Affiliation.** An author is only credited for a paper where OpenAlex tags
  *them* as UW-Madison-affiliated, so external co-authors don't leak in.
- **Cost control.** `explain` only calls Claude for the top `--top-k` matches of
  the first `--max-authors` people. Raise those once you're happy with results.
- **Tuning the field.** Edit `AI_CONCEPT_IDS` in `scholar_match/config.py` to
  narrow to pure stats, or widen to other areas.
```
