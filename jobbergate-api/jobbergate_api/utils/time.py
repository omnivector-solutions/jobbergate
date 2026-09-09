"""Helpers for handling datetime values coming from the API boundary."""

from datetime import datetime, timezone


def ensure_utc(value: datetime | None) -> datetime | None:
    """Interpret timezone-naive values as UTC so they can be compared with aware timestamps."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
