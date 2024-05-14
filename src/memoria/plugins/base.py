from abc import ABC
from contextlib import AbstractAsyncContextManager
from dataclasses import dataclass, field
from typing import Any, Optional


class Plugin(AbstractAsyncContextManager, ABC):
    async def __aexit__(self, *_, **__):
        """Overridden here so as to satisfy the abstractmethod."""
        return None


@dataclass(slots=True, eq=False, repr=False, match_args=False, kw_only=True)
class Result:
    """Describes the result of extraction or filtering."""
    url: str
    request_url: str
    content: Any

    content_type: str
    encoding: str | None

    meta: dict[str, str] = field(default_factory=dict)
    original: Optional['Result'] = None
