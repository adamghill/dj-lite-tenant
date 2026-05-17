import threading
import time
from collections import OrderedDict

_lock = threading.Lock()
_registry: OrderedDict[str, float] = OrderedDict()  # alias -> last_access monotonic time


def touch(alias: str) -> None:
    """Mark alias as recently used."""
    with _lock:
        _registry[alias] = time.monotonic()
        _registry.move_to_end(alias)


def evict_if_needed(max_connections: int) -> None:
    """Evict least-recently-used aliases when over the limit."""
    with _lock:
        while len(_registry) > max_connections:
            alias, _ = _registry.popitem(last=False)  # LRU = first item
            _close_alias(alias)


def remove(alias: str) -> None:
    """Remove an alias from the registry without closing (caller handles close)."""
    with _lock:
        _registry.pop(alias, None)


def _close_alias(alias: str) -> None:
    from django.conf import settings
    from django.db import connections

    if alias in connections:
        connections[alias].close()
        del connections[alias]

    settings.DATABASES.pop(alias, None)
