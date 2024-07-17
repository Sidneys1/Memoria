from typing import TYPE_CHECKING, Coroutine, AsyncIterable

from ..model.source import Source
from ..model.orm.configured_source import ConfiguredSource

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

def get_sources(session: 'AsyncSession', skip: int = 0, limit: int|None = None) -> Coroutine[None, None, AsyncIterable[ConfiguredSource]]:
    return ConfiguredSource.find_all(session, skip=skip, limit=limit, order_by=ConfiguredSource.id.desc())
