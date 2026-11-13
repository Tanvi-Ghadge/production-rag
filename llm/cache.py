from __future__ import annotations

import hashlib


class ExactCache:
    def __init__(self, redis_url: str | None = None) -> None:
        self._values: dict[str, str] = {}
        self._redis = None
        self.last_hit = False
        if redis_url:
            try:
                import redis
                self._redis = redis.Redis.from_url(
                    redis_url,
                    decode_responses=True,
                    socket_connect_timeout=1,
                    socket_timeout=1,
                )
            except Exception:
                self._redis = None

    def _key(self, value: str) -> str:
        return "rag:llm:" + hashlib.sha256(value.encode()).hexdigest()

    def get(self, value: str) -> str | None:
        key = self._key(value)
        try:
            result = self._redis.get(key) if self._redis else self._values.get(key)
        except Exception:
            result = self._values.get(key)
        self.last_hit = result is not None
        return result

    def set(self, value: str, result: str, ttl: int = 3600) -> None:
        key = self._key(value)
        self._values[key] = result
        try:
            if self._redis:
                self._redis.setex(key, ttl, result)
        except Exception:
            pass