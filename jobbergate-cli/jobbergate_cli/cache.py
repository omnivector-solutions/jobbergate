"""
Provide in-memory, client-scoped caching utilities shared by the CLI tool functions.
"""

import threading
import weakref
from typing import Generic, TypeVar

import httpx

CacheKey = int | str

V = TypeVar("V")


class ClientScopedCache(Generic[V]):
    """
    An in-memory cache scoped per ``httpx.Client``.

    Clients are held through weak references, so cache entries vanish along with the client
    (each ``JobbergateContext`` owns a single client for its whole lifetime). Access is guarded
    by a lock, but the lock is never held during network I/O; concurrent misses may duplicate a
    download, yet they can never corrupt the cache.
    """

    def __init__(self) -> None:
        self._entries: "weakref.WeakKeyDictionary[httpx.Client, dict[CacheKey, V]]" = weakref.WeakKeyDictionary()
        self._lock = threading.Lock()

    def get(self, client: httpx.Client, key: CacheKey) -> V | None:
        """
        Get the value cached under ``key`` for ``client``, or ``None`` on a miss.
        """
        with self._lock:
            return self._entries.get(client, {}).get(key)

    def set(self, client: httpx.Client, key: CacheKey, value: V, *alias_keys: CacheKey | None) -> None:
        """
        Store ``value`` under ``key`` (and any non-``None`` ``alias_keys``) for ``client``.

        Alias keys allow the same entry to be found under equivalent identities, e.g. an
        application's ``id`` and its ``identifier``.
        """
        with self._lock:
            entries = self._entries.setdefault(client, {})
            entries[key] = value
            for alias_key in alias_keys:
                if alias_key is not None:
                    entries[alias_key] = value

    def clear(self) -> None:
        """
        Clear all cached entries for all clients.
        """
        with self._lock:
            self._entries.clear()
