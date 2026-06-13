"""Shared configuration and constants."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# --- Paths ---------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

WORKS_PATH = DATA_DIR / "works.json"          # raw publications from OpenAlex
PROFILES_PATH = DATA_DIR / "profiles.json"     # one entry per author
MATCHES_PATH = DATA_DIR / "matches.json"       # ranked pairs + similarity
EXPLAINED_PATH = DATA_DIR / "matches_explained.json"  # + LLM explanations

# --- OpenAlex ------------------------------------------------------------
OPENALEX_BASE = "https://api.openalex.org"
OPENALEX_MAILTO = os.getenv("OPENALEX_MAILTO", "")

# University of Wisconsin-Madison in OpenAlex.
# https://openalex.org/I135310074  (ROR: https://ror.org/01y2jtd41)
UW_MADISON_ID = "I135310074"

# OpenAlex concept IDs used to scope "AI-related" work. A work matches if it is
# tagged with ANY of these concepts. Statistics is included on purpose so the
# stats-flavored ML crowd is captured (see the user's "focus on stats" ask).
# https://docs.openalex.org/api-entities/concepts
AI_CONCEPT_IDS = {
    "C154945302": "Artificial intelligence",
    "C119857082": "Machine learning",
    "C108583219": "Deep learning",
    "C50644808": "Artificial neural network",
    "C204321447": "Natural language processing",
    "C31972630": "Computer vision",
    "C105795698": "Statistics",
    "C156237330": "Statistical learning / inference",
}

# --- Models --------------------------------------------------------------
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # sentence-transformers; small + fast
CLAUDE_MODEL = "claude-opus-4-8"      # match-explanation step
