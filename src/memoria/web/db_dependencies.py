from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated, Optional

from fastapi import Depends

from ..settings import SETTINGS

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch
    from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

#### ElasticSearch ####

CLIENT: Optional['AsyncElasticsearch'] = None


@asynccontextmanager
async def es_lifecycle():
    from elasticsearch import AsyncElasticsearch

    basic_auth = (SETTINGS.elastic_user, SETTINGS.elastic_password)

    global CLIENT
    CLIENT = AsyncElasticsearch(SETTINGS.elastic_host, basic_auth=basic_auth)
    yield
    await CLIENT.close()


async def get_elasticsearch() -> 'AsyncElasticsearch':
    assert CLIENT is not None
    return CLIENT


Elasticsearch = Annotated['AsyncElasticsearch', Depends(get_elasticsearch)]

#### SQLAlchemy ####

ENGINE: Optional['AsyncEngine'] = None
SESSION_MAKER: Optional['async_sessionmaker[AsyncSession]'] = None


async def get_session():
    async with SESSION_MAKER() as session:
        try:
            yield session
        finally:
            await session.close()


SqlSession = Annotated['AsyncSession', Depends(get_session)]


@asynccontextmanager
async def sqlalchemy_lifecycle():
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from ..model.orm import CrudBase

    global ENGINE
    global SESSION_MAKER
    try:
        ENGINE = create_async_engine(SETTINGS.database_uri, connect_args={"check_same_thread": False})
        SESSION_MAKER = async_sessionmaker(ENGINE, autocommit=False, autoflush=False, expire_on_commit=False)
        async with ENGINE.begin() as conn:
            await conn.run_sync(CrudBase.metadata.create_all)
        yield
    finally:
        await ENGINE.dispose()
