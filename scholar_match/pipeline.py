"""CLI entry point. Run stages individually or end-to-end.

    python -m scholar_match.pipeline all
    python -m scholar_match.pipeline fetch --from-year 2019 --max-works 3000
    python -m scholar_match.pipeline profiles --min-works 3
    python -m scholar_match.pipeline match --top-k 5
    python -m scholar_match.pipeline explain --max-authors 25 --top-k 2
"""

from __future__ import annotations

import argparse

from . import openalex, profiles, matching, explain, report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="stage", required=True)

    p_fetch = sub.add_parser("fetch", help="Pull AI works from OpenAlex")
    p_fetch.add_argument("--from-year", type=int, default=2018)
    p_fetch.add_argument("--max-works", type=int, default=None)

    p_prof = sub.add_parser("profiles", help="Group works into author profiles")
    p_prof.add_argument("--min-works", type=int, default=2)
    p_prof.add_argument("--max-works-per-author", type=int, default=20)

    p_match = sub.add_parser("match", help="Rank similar authors")
    p_match.add_argument("--top-k", type=int, default=5)

    p_exp = sub.add_parser("explain", help="LLM explanations for top matches")
    p_exp.add_argument("--top-k", type=int, default=2)
    p_exp.add_argument("--max-authors", type=int, default=25)

    sub.add_parser("report", help="Build a browsable report.html from results")

    p_all = sub.add_parser("all", help="Run every stage")
    p_all.add_argument("--from-year", type=int, default=2018)
    p_all.add_argument("--max-works", type=int, default=None)
    p_all.add_argument("--min-works", type=int, default=2)
    p_all.add_argument("--top-k", type=int, default=5)
    p_all.add_argument("--explain-top-k", type=int, default=2)
    p_all.add_argument("--max-authors", type=int, default=25)
    p_all.add_argument("--skip-explain", action="store_true")

    args = parser.parse_args()

    if args.stage == "fetch":
        openalex.fetch_and_save(from_year=args.from_year, max_works=args.max_works)
    elif args.stage == "profiles":
        profiles.build_and_save(
            min_works=args.min_works,
            max_works_per_author=args.max_works_per_author,
        )
    elif args.stage == "match":
        matching.rank_and_save(top_k=args.top_k)
    elif args.stage == "explain":
        explain.explain_and_save(top_k=args.top_k, max_authors=args.max_authors)
    elif args.stage == "report":
        report.build_report()
    elif args.stage == "all":
        works = openalex.fetch_and_save(
            from_year=args.from_year, max_works=args.max_works
        )
        profs = profiles.build_and_save(works=works, min_works=args.min_works)
        matching.rank_and_save(profiles=profs, top_k=args.top_k)
        if not args.skip_explain:
            explain.explain_and_save(
                top_k=args.explain_top_k, max_authors=args.max_authors
            )
        report.build_report()


if __name__ == "__main__":
    main()
