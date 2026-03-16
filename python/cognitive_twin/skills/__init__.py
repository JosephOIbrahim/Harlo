"""Skills observer — competence tracking via incremental trace analysis."""

from .observer import (
    ObserverCursor,
    initial_cursor,
    observe_traces,
    query_skills,
)

__all__ = [
    "ObserverCursor",
    "initial_cursor",
    "observe_traces",
    "query_skills",
]
