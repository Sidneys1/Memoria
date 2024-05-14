from abc import ABC
from typing import ClassVar

from .base import Result, Plugin


class Extractor(Plugin, ABC):
    accept: ClassVar[set[str]]

    async def extract(self, input_: Result) -> Result:
        """Extract plain-text content from an input."""
