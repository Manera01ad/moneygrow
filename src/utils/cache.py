from typing import Optional, Any
import time

class SimpleCache:
    """Simple in-memory cache (use Redis in production)"""
    def __init__(self):
        self._cache = {}
        self._ttl = 300  # 5 minutes default

    def get(self, key: str) -> Optional[Any]:
        if key in self._cache:
            entry = self._cache[key]
            if time.time() < entry['expires']:
                return entry['value']
            else:
                del self._cache[key]
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        self._cache[key] = {
            'value': value,
            'expires': time.time() + (ttl or self._ttl)
        }

    def clear(self):
        self._cache.clear()

cache = SimpleCache()
