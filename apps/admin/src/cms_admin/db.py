"""Thread-affine storage access.

Storage backends are synchronous and thread-affine (a SQLite connection must
be used on the thread that opened it). The admin opens one backend per
process on a dedicated single-thread executor and funnels every call to it —
correct for every engine and serialized by construction.
"""

import asyncio
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor

from cms_core.storage import StorageBackend, create_storage


class StorageExecutor:
    def __init__(self, url: str) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="storage")
        self._storage = self._executor.submit(create_storage, url).result()
        self._closed = False

    @property
    def closed(self) -> bool:
        return self._closed

    async def run[T](self, operation: Callable[[StorageBackend], T]) -> T:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, operation, self._storage)

    def close(self) -> None:
        if not self._closed:
            self._executor.submit(self._storage.close).result()
            self._executor.shutdown()
            self._closed = True
