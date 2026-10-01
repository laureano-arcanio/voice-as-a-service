import ipaddress
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from .errors import ServiceError

MAX_KEYS = 10_000


class RateLimited(ServiceError):
    status_code = 429
    default_code = "rate_limited"

    def __init__(self, message: str, retry_after: int):
        super().__init__(message)
        self.retry_after = retry_after


@dataclass(frozen=True)
class Limit:
    max_hits: int
    window_seconds: int


class RateLimiter:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.hits: dict[str, deque[float]] = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: str, limits: list[Limit], message: str) -> None:
        now = self.clock()
        longest = max(limit.window_seconds for limit in limits)
        with self.lock:
            hits = self.hits[key]
            while hits and now - hits[0] >= longest:
                hits.popleft()
            for limit in limits:
                recent = [t for t in hits if now - t < limit.window_seconds]
                if len(recent) >= limit.max_hits:
                    raise RateLimited(message, int(limit.window_seconds - (now - recent[0])) + 1)

    def hit(self, key: str) -> None:
        with self.lock:
            if len(self.hits) >= MAX_KEYS:
                self._sweep()
            self.hits[key].append(self.clock())

    def consume(self, key: str, limits: list[Limit], message: str) -> None:
        self.check(key, limits, message)
        self.hit(key)

    def reset(self) -> None:
        with self.lock:
            self.hits.clear()

    def _sweep(self) -> None:
        now = self.clock()
        for key in [k for k, v in self.hits.items() if not v or now - v[-1] >= 86_400]:
            del self.hits[key]


def client_key(ip: str) -> str:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return ip
    if addr.version == 6:
        return str(ipaddress.ip_network(f"{addr}/64", strict=False))
    return str(addr)
