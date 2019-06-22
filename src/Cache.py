import time, typing, uuid

class Cache(object):
    def __init__(self):
        self._items = {}
        self._item_to_id = {}

    def cache(self, item: typing.Any) -> str:
        return self._cache(item, None)
    def temporary_cache(self, item: typing.Any, timeout: float)-> str:
        return self._cache(item, time.monotonic()+timeout)
    def _cache(self, item: typing.Any, timeout: typing.Optional[float]) -> str:
        id = str(uuid.uuid4())
        self._items[id] = [item, timeout]
        self._item_to_id[item] = id
        return id

    def next_expiration(self) -> typing.Optional[float]:
        expirations = [self._items[id][1] for id in self._items]
        expirations = list(filter(None, expirations))
        if not expirations:
            return None
        now = time.monotonic()
        expirations = [e-now for e in expirations]
        return max(min(expirations), 0)

    def expire(self):
        now = time.monotonic()
        expired = []
        for id in self._items:
            item, expiration = self._items[id]
            if expiration and expiration <= now:
                expired.append(id)
        for id in expired:
            item, expiration = self._items[id]
            del self._items[id]
            del self._item_to_id[item]

    def has_item(self, item: typing.Any) -> bool:
        return item in self._item_to_id

    def get(self, id: str) -> typing.Any:
        item, expiration = self._items[id]
        return item

    def get_expiration(self, item: typing.Any) -> float:
        id = self._item_to_id[item]
        item, expiration = self._items[id]
        return expiration
    def until_expiration(self, item: typing.Any) -> float:
        expiration = self.get_expiration(item)
        return expiration-time.monotonic()
