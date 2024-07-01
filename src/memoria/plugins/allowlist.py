from abc import ABC, abstractmethod
from functools import lru_cache
from typing import TYPE_CHECKING, NewType, Iterable, ClassVar, Sequence
from urllib.parse import ParseResult
from dataclasses import dataclass

if TYPE_CHECKING:
    from urllib.parse import ParseResult

from . import Plugin, Html

type Url = str
Hostname = NewType('Hostname', str)
PluginId = NewType('PluginId', str)
type InputItem = tuple[Hostname, Url, 'ParseResult']


class AllowlistRule(Plugin, ABC):
    @dataclass(repr=False, eq=False, match_args=False, slots=True, kw_only=True)
    class DisplayOptions:
        color: str|None = None
        prefix: str|None = None
        display_name: str|None = None

    DISPLAY_OPTIONS: ClassVar[DisplayOptions|None] = None
    """Used for UI/UX display purposes. Can be `None`."""

    LONG_DOCUMENTATION: ClassVar[Html|None] = None
    """Long (up to several paragraphs) HTML documentation. Used for UI/UX display purposes. Can be `None`."""

    SHORT_DOCUMENTATION: ClassVar[Html|None] = None
    """Short (up to a paragraph) HTML documentation. Used for UI/UX display purposes. Can be `None`."""

    LONG_DOC_EXAMPLES: ClassVar[Sequence[tuple[str, Html]]|None] = None
    """Examples for use with the long HTML documentation. Lists of (example_value, html_description). Used for UI/UX display purposes. Can be `None`."""

    @classmethod
    @property
    @lru_cache
    def identifier(cls) -> PluginId:
        if cls.__name__.endswith('AllowlistRule'):
            return PluginId(cls.__name__[:-13])
        return PluginId(cls.__name__)

    @abstractmethod
    async def matches(self, item: InputItem, rules: Iterable[str]) -> bool:
        ...
