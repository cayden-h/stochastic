"""Deterministic deal math. Pure functions, no side effects.

The model never produces a number. Agents call these functions.
"""
from __future__ import annotations


def leverage(debt: float, ebitda: float) -> float:
    """Total debt divided by EBITDA, in turns (x)."""
    if ebitda <= 0:
        raise ValueError("ebitda must be positive")
    return debt / ebitda


def total_debt(existing_senior: float, instruments: dict[str, float], preferred_counts_as_debt: bool) -> float:
    """Existing senior debt plus new debt. Preferred counts only if the reading says so."""
    debt = existing_senior + instruments.get("senior", 0.0) + instruments.get("junior", 0.0)
    if preferred_counts_as_debt:
        debt += instruments.get("preferred", 0.0)
    return debt


def leverage_breach(
    existing_senior: float,
    ebitda: float,
    instruments: dict[str, float],
    limit: float,
    preferred_counts_as_debt: bool,
) -> tuple[bool, float]:
    """Return (breaches_limit, leverage_in_turns)."""
    lev = leverage(total_debt(existing_senior, instruments, preferred_counts_as_debt), ebitda)
    return lev > limit, round(lev, 2)
