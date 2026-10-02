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

    def _check_locked(self, key: str, limits: list[Limit], message: str, now: float) -> None:
        # get: una clave consultada (y rechazada) no queda en memoria.
        hits = self.hits.get(key)
        if not hits:
            return
        longest = max(limit.window_seconds for limit in limits)
        while hits and now - hits[0] >= longest:
            hits.popleft()
        for limit in limits:
            recent = [t for t in hits if now - t < limit.window_seconds]
            if len(recent) >= limit.max_hits:
                raise RateLimited(message, int(limit.window_seconds - (now - recent[0])) + 1)

    def _hit_locked(self, key: str, now: float) -> None:
        if len(self.hits) >= MAX_KEYS:
            self._sweep()
        self.hits[key].append(now)

    def check(self, key: str, limits: list[Limit], message: str) -> None:
        with self.lock:
            self._check_locked(key, limits, message, self.clock())

    def hit(self, key: str) -> None:
        with self.lock:
            self._hit_locked(key, self.clock())

    def consume(self, key: str, limits: list[Limit], message: str) -> None:
        """check + hit atomicos: pedidos en paralelo no pasan todos antes de contarse."""
        self.consume_all([(key, limits)], message)

    def consume_all(self, entries: list[tuple[str, list[Limit]]], message: str) -> None:
        """Chequea todas las claves y, si ninguna esta al tope, las cuenta (todo bajo el lock)."""
        with self.lock:
            now = self.clock()
            for key, limits in entries:
                self._check_locked(key, limits, message, now)
            for key, _ in entries:
                self._hit_locked(key, now)

    def unhit(self, key: str) -> None:
        """Descuenta el ultimo pedido de `key` (el que salio bien)."""
        with self.lock:
            hits = self.hits.get(key)
            if hits:
                hits.pop()
                if not hits:
                    del self.hits[key]

    def count(self, key: str, window_seconds: int) -> int:
        with self.lock:
            now = self.clock()
            return sum(1 for t in self.hits.get(key) or () if now - t < window_seconds)

    def reset(self, key: str | None = None) -> None:
        """Borra los pedidos de `key`, o todos sin key."""
        with self.lock:
            if key is None:
                self.hits.clear()
            else:
                self.hits.pop(key, None)

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
