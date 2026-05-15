# ADR-001: Per-User SQLite Connection Lifecycle

- **Status:** Proposed
- **Deciders:** adamghill
- **Date:** 2026-05-15

---

## Context

`django-sqlite-tenant` opens a new SQLite connection for every HTTP request and closes it at the end of the request (by deleting the alias from `connections` and `settings.DATABASES`). This is the simplest correct approach and avoids cross-user connection leaks.

However, it has a measurable cost at scale:

- SQLite `open()` + WAL PRAGMA initialisation on every request (~1–3ms per request)
- `CONN_MAX_AGE` (Django's built-in persistent connection mechanism) is bypassed entirely because the alias is deleted
- With N gunicorn workers and M active users, up to N × M file handles may be open simultaneously if connections are kept alive — but currently they are not, so the overhead is paid on every request instead

Oliver Andrich (who has implemented a similar system) noted that in Go this is addressed by a shared connection map per user keyed in a central store, accessible across goroutines. In Python/Django the thread-local connection store makes this harder to replicate without care.

## Decision Drivers

- Correctness: no user can ever read/write another user's connection
- Simplicity: as usable as possible, no exotic Python features required
- Performance: reduce per-request open/close overhead for active users
- Compatibility: works with standard Django, gunicorn (sync), and ASGI (async via daphne/uvicorn)

## Considered Options

### Option A — Current approach (open/close per request)

Keep deleting and re-registering the alias each request.

- ✅ Simplest, no leaks, safe
- ❌ Pays SQLite open cost + PRAGMA init on every request
- ❌ Defeats `CONN_MAX_AGE`

### Option B — Persistent alias + `CONN_MAX_AGE`

Register the user DB alias once (on first use) and never delete it from `settings.DATABASES`. Let Django's normal `CONN_MAX_AGE` mechanism keep the connection alive between requests on the same thread.

- ✅ Reuses open connections across requests on the same worker thread
- ✅ Standard Django mechanism, no custom pooling logic
- ⚠️ Aliases accumulate in `settings.DATABASES` as users log in — needs bounding
- ⚠️ With many users, thread-local connections across N workers × M users means N×M file handles may stay open
- ❌ Must ensure the alias is registered before the router is called (handled by middleware)

### Option C — LRU connection cache per worker

Keep an in-process LRU cache (keyed by `user_id`, bounded by a configurable `MAX_OPEN_USER_CONNECTIONS` setting). When the cache is full, evict the least-recently-used connection before opening a new one.

- ✅ Bounds memory and file descriptor usage
- ✅ Hot users (frequent requests on same worker) pay near-zero open cost
- ⚠️ More complex to implement correctly with Django's connection layer
- ⚠️ Must interact with Django's `connections` object rather than bypass it

## Decision

**Implement Option B for v0.2, with a bounded alias registry (partial Option C).**

Specifically:

- The middleware registers the user DB alias on first use and does **not** delete it at request end
- A module-level `dict` (one per worker process) tracks registered aliases and their last-access timestamp
- When the number of registered aliases exceeds `DJANGO_SQLITE_TENANT["MAX_OPEN_CONNECTIONS"]` (default: `100`), the middleware evicts the least-recently-used alias: closes its connection and removes it from `settings.DATABASES`
- `CONN_MAX_AGE` for user DB aliases is set to the value from `DJANGO_SQLITE_TENANT["CONN_MAX_AGE"]` (default: `600` seconds, same as Django's default recommendation)

This is implementable without any exotic Python, works with standard sync Django (gunicorn), and degrades gracefully: evicted connections are simply re-opened on next request.

## Consequences

- **Positive:** Active users pay the SQLite open cost at most once per `CONN_MAX_AGE` seconds per worker
- **Positive:** `settings.DATABASES` stays bounded in size
- **Positive:** No changes required to routers or signals
- **Negative:** The alias registry is per-process; under multi-process gunicorn, each worker has its own registry (this is correct and expected)
- **Negative:** Eviction logic adds ~20 lines of complexity to `middleware.py` and `utils.py`
- **Out of scope:** Shared cross-process connection pools (would require a separate server process and is not worth the complexity for SQLite)

## Implementation Notes

```python
# django_sqlite_tenant/connection_registry.py
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


def _close_alias(alias: str) -> None:
    from django.conf import settings
    from django.db import connections

    if alias in connections:
        connections[alias].close()
        del connections[alias]
    settings.DATABASES.pop(alias, None)
```

This module is intentionally simple and does not require any third-party dependencies.

## References

- Oliver Andrich's note: https://social.tchncs.de/@oliverandrich/116578697387580484
- Django `CONN_MAX_AGE` docs: https://docs.djangoproject.com/en/stable/ref/databases/#persistent-connections
