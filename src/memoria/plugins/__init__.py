from abc import ABC
from contextlib import AbstractAsyncContextManager
from typing import TypeAlias

Html: TypeAlias = str

class Plugin(AbstractAsyncContextManager, ABC):
    async def __aexit__(self, *_, **__):
        """Overridden here so as to satisfy the abstractmethod."""
        return None
