from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from .settings import SETTINGS

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch

async def create_elasticsearch_client(host: str, **kwargs) -> 'AsyncElasticsearch':
    from elasticsearch import AsyncElasticsearch

    from .elasticsearch import check_es_indexes

    es = AsyncElasticsearch(host, **kwargs)

    await check_es_indexes(es)

    return es

@asynccontextmanager
async def create_sql_client():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from .model.orm import CrudBase

    global ENGINE
    global SESSION_MAKER
    try:
        ENGINE = create_async_engine(SETTINGS.database_uri, connect_args={"check_same_thread": False})
        SESSION_MAKER = async_sessionmaker(ENGINE, autocommit=False, autoflush=False, expire_on_commit=False)
        async with ENGINE.begin() as conn:
            await conn.run_sync(CrudBase.metadata.create_all)
        async with SESSION_MAKER() as session:
            yield session
    finally:
        await ENGINE.dispose()
