"""Match UW-Madison scholars by overlap in their AI/ML/stats publications.

Pipeline:
    openalex  -> fetch AI-related works affiliated with UW-Madison
    profiles  -> group works by author into text profiles
    matching  -> embed profiles, rank pairs by cosine similarity
    explain   -> ask Claude to describe each top match in plain language
"""

__version__ = "0.1.0"
