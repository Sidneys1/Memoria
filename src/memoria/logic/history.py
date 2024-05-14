from typing import TYPE_CHECKING, AsyncIterable, Coroutine

# from ..model.imported_history import History
from ..model.orm.history import History

if TYPE_CHECKING:
    # from elasticsearch import AsyncElasticsearch
    from sqlalchemy.ext.asyncio import AsyncSession


def get_history(session: 'AsyncSession', skip: int = 0, limit: int|None = None) -> Coroutine[None, None, AsyncIterable[History]]:
    return History.find_all(session, order_by=History.last_scrape, skip=skip, limit=limit)
