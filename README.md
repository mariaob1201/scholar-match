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
| report | `scholar_match/report.py` | render results into a browsable `report.html` |

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
python -m scholar_match.pipeline report
```

Outputs land in `data/` as JSON:

- `works.json` — raw publications
- `profiles.json` — per-author profiles
- `matches.json` — ranked similar-author pairs + cosine scores
- `matches_explained.json` — the above, plus Claude's match explanations
- `report.html` — browsable report (see below)

## See the results

The `report` stage (run automatically by `all`) writes a single
self-contained **`data/report.html`** — no server needed:

```bash
python -m scholar_match.pipeline report
open data/report.html          # macOS  (xdg-open on Linux)
```

Two tabs at the top:

- **List** — each scholar with research-area chips and their top matches: a
  similarity bar + score per match, plus Claude's shared themes, summary, and
  collaboration idea. Search box filters by name or area.
- **Graph** — a force-directed network of who matches whom. Node size = number
  of AI papers, edge thickness = match strength, node color groups by primary
  area. Drag nodes to rearrange; click one to open its OpenAlex page.

Names link to OpenAlex. The report reads `matches_explained.json` when present,
otherwise falls back to `matches.json` (bars/scores only, no explanations).

### Why am I only seeing a few people?

The report header shows `… N scholars matched`. If `N` is small, you fetched or
kept too few authors — the fix is upstream, not in the report:

| Knob | Where | Effect |
|------|-------|--------|
| `--max-works` | `fetch` / `all` | Caps how many publications are pulled. **Omit it** to fetch everything (there are thousands). |
| `--from-year` | `fetch` / `all` | Earlier year ⇒ more works and authors. |
| `--min-works` | `profiles` / `all` | Authors with fewer AI papers than this are dropped. Lower to `1` to keep everyone. |

The `profiles` stage prints how many distinct UW authors it saw and how many it
dropped, so you can see exactly where people fall off. A full run keeps everyone:

```bash
python -m scholar_match.pipeline all --from-year 2020 --min-works 1
```

(`--max-authors`/`--top-k` on `explain` only limit how many get an LLM
write-up — everyone still appears in the report with similarity scores.)

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
