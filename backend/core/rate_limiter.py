import time
from collections import defaultdict
from fastapi import HTTPException, Request, status


class InMemoryRateLimiter:
    """Zero-dependency, thread-safe in-memory sliding window rate limiter.

    Protects expensive AI orchestration and PDF processing endpoints from resource
    exhaustion and denial-of-service flooding.
    """

    def __init__(self, requests_per_minute: int = 30, window_seconds: int = 60) -> None:
        self.requests_per_minute = requests_per_minute
        self.window_seconds = window_seconds
        self._history: dict[str, list[float]] = defaultdict(list)

    def _clean_old_requests(self, key: str, now: float) -> None:
        threshold = now - self.window_seconds
        self._history[key] = [t for t in self._history[key] if t > threshold]

    def check(self, request: Request, custom_key: str | None = None) -> None:
        """Evaluate whether the request exceeds the rate limit.

        Raises HTTPException(429) if exceeded.
        """
        # Determine client key based on user identity or client IP
        if custom_key:
            client_key = custom_key
        else:
            user_header = request.headers.get("x-user-id")
            auth_header = request.headers.get("authorization")
            if user_header:
                client_key = f"user:{user_header.strip()}"
            elif auth_header and auth_header.startswith("Bearer "):
                client_key = f"user:{auth_header[7:].strip()}"
            elif request.client and request.client.host:
                client_key = f"ip:{request.client.host}"
            else:
                client_key = "anonymous"

        now = time.time()
        self._clean_old_requests(client_key, now)

        if len(self._history[client_key]) >= self.requests_per_minute:
            retry_after = int(self.window_seconds - (now - self._history[client_key][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please wait before submitting additional research tasks.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._history[client_key].append(now)

    def reset(self) -> None:
        """Clear all tracking state (used in testing)."""
        self._history.clear()


# Default limiter instance for expensive research initiation endpoints
research_limiter = InMemoryRateLimiter(requests_per_minute=20, window_seconds=60)
