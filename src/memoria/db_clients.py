from contextlib import asynccontextmanager
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING

from .settings import SETTINGS
from .util import set_context_var

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch
    from sqlalchemy.ext.asyncio import AsyncSession

async def create_elasticsearch_client(host: str, **kwargs) -> 'AsyncElasticsearch':
    from elasticsearch import AsyncElasticsearch

    from .elasticsearch import check_es_indexes

    es = AsyncElasticsearch(host, **kwargs)

    await check_es_indexes(es)

    return es

_SQL_CLIENT: ContextVar['AsyncSession'] = ContextVar('_SQL_CLIENT')

def get_sql_client() -> 'AsyncSession':
    return _SQL_CLIENT.get()

@asynccontextmanager
async def create_sql_client():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from .model.orm import CrudBase

    global ENGINE
    global SESSION_MAKER
    if (client := _SQL_CLIENT.get(None)) is not None:
        yield client
        return
    try:
        ENGINE = create_async_engine(SETTINGS.database_uri, connect_args={"check_same_thread": False})
        SESSION_MAKER = async_sessionmaker(ENGINE, autocommit=False, autoflush=False, expire_on_commit=False)
        async with ENGINE.begin() as conn:
            await conn.run_sync(CrudBase.metadata.create_all)
        async with SESSION_MAKER() as session, set_context_var(_SQL_CLIENT, session):
            yield session
    finally:
        await ENGINE.dispose()
        ENGINE = None
