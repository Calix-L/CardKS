"""Known official duplicate-scoring utilities for competitive Dou Dizhu."""

from __future__ import annotations

from dataclasses import dataclass
from numbers import Real


@dataclass(frozen=True)
class MatchpointResult:
    raw_score: float
    matchpoints: int
    top: int
    rate: float
    rank: int


def matchpoints(raw_scores: list[Real]) -> list[MatchpointResult]:
    """Compare same-board, same-position raw scores using official 2/1/0 MP.

    Each score receives two points per lower result, one per equal result and
    zero per higher result. Tied results share a competition rank, with later
    ranks skipped (1, 1, 3 ...).
    """

    if len(raw_scores) < 2:
        raise ValueError("at least two comparable scores are required")
    if any(isinstance(value, bool) or not isinstance(value, Real) for value in raw_scores):
        raise ValueError("raw scores must be numeric")
    top = 2 * (len(raw_scores) - 1)
    output: list[MatchpointResult] = []
    for value in raw_scores:
        lower = sum(value > other for other in raw_scores)
        equal_other = sum(value == other for other in raw_scores) - 1
        mp = 2 * lower + equal_other
        rank = 1 + sum(other > value for other in raw_scores)
        output.append(MatchpointResult(float(value), mp, top, mp / top * 100.0, rank))
    return output
