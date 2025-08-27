import asyncio

class ApiRateLimiter:
    """
    Limiter for Clash Royale Api calling: max N calls per second.
    """
    def __init__(self, per_second: float):
        self.interval = 1.0 / per_second
        self._lock = asyncio.Lock()
        self._next_at = 0.0  # timestamp, at which the next call is allowed to happen

    async def __aenter__(self):
        async with self._lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            wait = self._next_at - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = loop.time()
            # Reserve the next time slot
            self._next_at = now + self.interval
        # Release lock; exactly ONE task per interval

    async def __aexit__(self, exc_type, exc, tb):
        return False