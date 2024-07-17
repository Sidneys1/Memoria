from abc import ABC
from dataclasses import dataclass
from typing import AsyncIterator, ClassVar, Protocol, Callable, Coroutine, AsyncGenerator

from pydantic import JsonValue

from ..model.imported_history import ImportedHistory
from . import Plugin, PluginSchedule, Html


class HistoryImporter(Protocol):
    async def add_many(self, items: AsyncIterator[ImportedHistory]) -> None:
        """"""

    async def add(self, item: ImportedHistory) -> None:
        """"""

    async def flush(self) -> None:
        """"""

class UxHost(Protocol):
    async def update_dialog(self, form: Html) -> 'JsonValue':
        ...

    async def done(self) -> None:
        ...

    async def waiting(self, text: Html|None = None) -> None:
        ...

    async def error(self, message: Html) -> None:
        ...


class Source(Plugin, ABC):
    @dataclass(repr=False, eq=False, match_args=False, slots=True, kw_only=True)
    class UxConfig:
        display_name: str|None = None
        description: str|None = None
        create: Callable[['UxHost'], Coroutine[None, None, tuple[Html, 'JsonValue']]]|None = None

    UX_CONFIG: ClassVar[UxConfig] = UxConfig()
    SUPPORTED_SCHEDULES: ClassVar[PluginSchedule]

    def __init__(self, config: JsonValue) -> None:
        super().__init__()

    async def run(self, importer: 'HistoryImporter') -> None:
        ...


