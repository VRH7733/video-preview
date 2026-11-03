"""In-memory store for preview clips, served to the browser by token. Nothing touches the disk."""

import secrets
import threading
from collections import OrderedDict

MAX_ITEMS = 16
MAX_BYTES = 256 * 1024 * 1024


class PreviewStore:
    def __init__(self, max_items=MAX_ITEMS, max_bytes=MAX_BYTES):
        self.max_items, self.max_bytes = max_items, max_bytes
        self._items = OrderedDict()
        self._lock = threading.Lock()

    def put(self, data):
        token = secrets.token_urlsafe(16)
        with self._lock:
            self._items[token] = data
            while len(self._items) > self.max_items or (
                    len(self._items) > 1 and sum(len(v) for v in self._items.values()) > self.max_bytes):
                self._items.popitem(last=False)
        return token

    def get(self, token):
        with self._lock:
            data = self._items.get(token)
            if data is not None:
                self._items.move_to_end(token)
            return data


PREVIEWS = PreviewStore()
