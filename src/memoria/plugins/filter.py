from abc import ABC
from typing import Any, ClassVar

from .base import Result, Plugin


class Filter(Plugin, ABC):
    accept: ClassVar[set[str]]
    content_types: ClassVar[set[str]]

    async def transform(self, input_: Result, want_content_types: set[str]) -> Result:
        """Transform the input in some way, producing the requested Content-Type."""
