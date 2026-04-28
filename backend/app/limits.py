"""Per-IP token-bucket rate limiter, applied to the cost-bearing routes.

We keep the limiter at module scope so route handlers can decorate
themselves at definition time. The bucket is in-memory — fine for a
single-container demo. For multi-instance deployment, swap in a Redis
storage backend (slowapi supports that out of the box).
"""

from __future__ import annotations

import os

from slowapi import Limiter
from slowapi.util import get_remote_address

RATE_LIMIT = f"{os.getenv('RATE_LIMIT_PER_MINUTE', '20')}/minute"

limiter = Limiter(key_func=get_remote_address, default_limits=[])
