import hashlib, time, typing, uuid
from src import PollHook

class Cache(PollHook.PollHook):
    def __init__(self):
        self._items = {}

        self._cached_expiration = None

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
        self._cached_expiration = None
        self._items[id] = [key, value, expiration]
        return id

    def next(self) -> typing.Optional[float]:
        if not self._cached_expiration == None:
            return self._cached_expiration

        expirations = [value[-1] for value in self._items.values()]
        expirations = list(filter(None, expirations))
        if not expirations:
            return None
        now = time.monotonic()
        expirations = [e-now for e in expirations]

        expiration = max(min(expirations), 0)
        self._cached_expiration = expiration
        return expiration

    def call(self):
        now = time.monotonic()
        expired = []
        for id in self._items.keys():
            key, value, expiration = self._items[id]
            if expiration and expiration <= now:
                expired.append(id)
        for id in expired:
            self._cached_expiration = None
            del self._items[id]

    def has_item(self, key: typing.Any) -> bool:
        return self.cache_key(key) in self._items

    def get(self, key: str) -> typing.Any:
        key, value, expiration = self._items[self.cache_key(key)]
        return value
    def remove(self, key: str):
        self._cached_expiration = None
        del self._items[self.cache_key(key)]

    def get_expiration(self, key: typing.Any) -> float:
        key, value, expiration = self._items[self.cache_key(key)]
        return expiration
    def until_expiration(self, key: typing.Any) -> float:
        expiration = self.get_expiration(key)
        return expiration-time.monotonic()
