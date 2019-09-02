import hashlib, time, typing, uuid

class Cache(object):
    def __init__(self):
        self._items = {}

    def cache_key(self, key: str):
        return "sha1:%s" % hashlib.sha1(key.encode("utf8")).hexdigest()

    def cache(self, key: str, value: typing.Any) -> str:
        return self._cache(key, value, None)
    def temporary_cache(self, key: str, value: typing.Any, timeout: float
            )-> str:
        return self._cache(key, value, time.monotonic()+timeout)
    def _cache(self, key: str, value: typing.Any,
            expiration: typing.Optional[float]) -> str:
        id = self.cache_key(key)
        self._items[id] = [key, value, expiration]
        return id

    def next_expiration(self) -> typing.Optional[float]:
        expirations = [value[-1] for value in self._items.values()]
        expirations = list(filter(None, expirations))
        if not expirations:
            return None
        now = time.monotonic()
        expirations = [e-now for e in expirations]
        return max(min(expirations), 0)

    def expire(self):
        now = time.monotonic()
        expired = []
        for id in self._items.keys():
            key, value, expiration = self._items[id]
            if expiration and expiration <= now:
                expired.append(id)
        for id in expired:
            del self._items[id]

    def has_item(self, key: typing.Any) -> bool:
        return self.cache_key(key) in self._items

    def get(self, key: str) -> typing.Any:
        key, value, expiration = self._items[self.cache_key(key)]
        return value
    def remove(self, key: str):
        del self._items[self.cache_key(key)]

    def get_expiration(self, key: typing.Any) -> float:
        key, value, expiration = self._items[self.cache_key(key)]
        return expiration
    def until_expiration(self, key: typing.Any) -> float:
        expiration = self.get_expiration(key)
        return expiration-time.monotonic()
