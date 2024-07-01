from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Optional

from . import Plugin


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


class _ProcessingPlugin(ABC):
    """Used purely for `issubclass(..., _ProcessingPlugin)` checks."""


class Downloader(Plugin, _ProcessingPlugin, ABC):
    content_types: ClassVar[set[str]]

    @abstractmethod
    async def download(self, url: str, want_content_types: set[str]) -> Result | None:
        """Download a given URL and produce the requested Content-Type, if possible."""


class Extractor(Plugin, _ProcessingPlugin, ABC):
    accept: ClassVar[set[str]]

    @abstractmethod
    async def extract(self, input_: Result) -> Result:
        """Extract plain-text content from an input."""


class Filter(Plugin, _ProcessingPlugin, ABC):
    accept: ClassVar[set[str]]
    content_types: ClassVar[set[str]]

    @abstractmethod
    async def transform(self, input_: Result, want_content_types: set[str]) -> Result:
        """Transform the input in some way, producing the requested Content-Type."""
