import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.config import settings

_EXEMPT = ("/health", "/docs", "/redoc", "/openapi.json")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window per-IP limiter. Uses Redis when reachable, otherwise in-process memory."""

    def __init__(self, app, limit: int | None = None):
        super().__init__(app)
        self.limit = limit or settings.rate_limit_per_minute
        self._redis = None
        self._redis_checked = False
        self._mem: dict[str, int] = defaultdict(int)

    def _get_redis(self):
        if not self._redis_checked:
            self._redis_checked = True
            try:
                import redis

                client = redis.Redis.from_url(
                    settings.redis_url, socket_connect_timeout=0.3, socket_timeout=0.3
                )
                client.ping()
                self._redis = client
            except Exception:
                self._redis = None
        return self._redis

    def _incr(self, key: str) -> int:
        r = self._get_redis()
        if r is not None:
            try:
                n = r.incr(key)
                if n == 1:
                    r.expire(key, 70)
                return int(n)
            except Exception:
                self._redis = None
        self._mem[key] += 1
        window = key.rsplit(":", 1)[-1]
        for k in [k for k in self._mem if not k.endswith(window)]:
            self._mem.pop(k, None)
        return self._mem[key]

    async def dispatch(self, request, call_next):
        if self.limit <= 0 or request.url.path in _EXEMPT:  # RATE_LIMIT_PER_MINUTE=0 disables limiting
            return await call_next(request)
        ip = request.client.host if request.client else "unknown"
        key = f"rl:{ip}:{int(time.time() // 60)}"
        if self._incr(key) > self.limit:
            return JSONResponse(
                {"detail": "Rate limit exceeded. Try again in a minute."},
                status_code=429,
                headers={"Retry-After": "60"},
            )
        return await call_next(request)
