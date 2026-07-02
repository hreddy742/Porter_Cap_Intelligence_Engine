"""Shared rate-limiter singleton.

Import ``limiter`` in any router that needs a ``@limiter.limit(...)``
decorator.  The FastAPI app wires the exception handler in ``create_app``
so 429 responses are formatted consistently with the rest of the API.

Storage: in-memory by default (per-process).  For multi-worker deployments
wire a Redis URI via ``Limiter(storage_uri=settings.redis_url)`` once a
Redis URL is added to config.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
