"""Shared time-normalization helper for hash-chain canonicalization.

SQLite returns naive ``datetime`` objects for timezone-aware columns
(Postgres does not) — so recomputing a hash from a freshly-queried row can
disagree with the value computed from the original in-memory object unless
both sides are normalized to the same explicit UTC representation first.
"""

from datetime import datetime, timezone


def to_utc(value: datetime) -> datetime:
    """Return an equivalent UTC-aware datetime, assuming UTC for naive input."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
