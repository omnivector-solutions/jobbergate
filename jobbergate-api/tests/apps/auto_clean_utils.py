"""Shared helpers for auto-clean service tests."""

from typing import Any, NamedTuple


class EntryInfo(NamedTuple):
    """Named tuple to store the info on a test entry."""

    last_updated_delta: int
    last_used_delta: int | None
    is_archived: bool


def filter_test_entries(
    entries: dict[EntryInfo, dict[str, Any]],
    **kwargs: set[Any],
) -> set[int]:
    """Filter test entry ids by matching EntryInfo attributes against provided sets."""
    if not kwargs:
        return set()
    return {value["id"] for key, value in entries.items() if all(getattr(key, k) in v for k, v in kwargs.items())}


def expected_archived_ids(entries: dict[EntryInfo, dict[str, Any]], time_delta: int) -> set[int]:
    """Expected archived ids based on the current test time delta."""
    return filter_test_entries(
        entries,
        is_archived={False},
        last_updated_delta=set(range(time_delta)),
        last_used_delta=set(range(time_delta)) | {None},
    )


def expected_deleted_ids(entries: dict[EntryInfo, dict[str, Any]], time_delta: int) -> set[int]:
    """Expected deleted ids based on the current test time delta."""
    return filter_test_entries(
        entries,
        is_archived={True},
        last_updated_delta=set(range(time_delta - 1)),
        last_used_delta=set(range(time_delta - 1)) | {None},
    )
