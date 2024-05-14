from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


@asynccontextmanager
async def lifespan(_: 'FastAPI'):
    from .db_dependencies import es_lifecycle, sqlalchemy_lifecycle
    async with es_lifecycle(), sqlalchemy_lifecycle():
        yield
