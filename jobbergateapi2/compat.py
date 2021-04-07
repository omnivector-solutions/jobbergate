"""
Definitions required for compatibility with other Python versions
or database drivers
"""

try:
    from typing import TypedDict  # type: ignore
except ImportError:  # pragma: nocover
    from typing_extensions import TypedDict


_integrity_exceptions = []
try:
    from asyncpg.exceptions import UniqueViolationError

    _integrity_exceptions.append(UniqueViolationError)
except ImportError:  # pragma: nocover
    "asyncpg not installed"

try:
    from aiosqlite import IntegrityError

    _integrity_exceptions.append(IntegrityError)
except ImportError:  # pragma: nocover
    "aiosqlite not installed"


INTEGRITY_CHECK_EXCEPTIONS = tuple(_integrity_exceptions)

__all__ = ["TypedDict", "INTEGRITY_CHECK_EXCEPTIONS"]
