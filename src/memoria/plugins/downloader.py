from abc import ABC
from typing import ClassVar

from .base import Result, Plugin

class Downloader(Plugin, ABC):
    content_types: ClassVar[set[str]]

    async def download(self, url: str, want_content_types: set[str]) -> Result | None:
        """Download a given URL and produce the requested Content-Type, if possible."""
