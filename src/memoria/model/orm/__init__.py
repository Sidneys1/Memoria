from typing import Any, AsyncIterable, Self

from sqlalchemy import Column as Col
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession
from sqlalchemy.orm import DeclarativeBase


class Column(Col):
    inherit_cache = True
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('nullable', False)
        super().__init__(*args, **kwargs)


class CrudBase(AsyncAttrs, DeclarativeBase):
    # @classmethod
    # def create(cls, db: Session, )

    @classmethod
    async def get(cls, session: AsyncSession, ident) -> Self:
        return await session.get(cls, ident)

    @classmethod
    async def find_one(cls, session: AsyncSession, filter_, *filters) -> Self | None:
        try:
            ret = select(cls).filter(filter_, *filters)
            return (await session.execute(ret)).scalars().one()
        except NoResultFound:
            return None

    @classmethod
    async def find_all(cls,
                       session: AsyncSession,
                       *filters,
                       order_by: Any | None = None,
                       skip: int = 0,
                       limit: int | None = None) -> AsyncIterable[Self]:
        ret = select(cls)
        if filters:
            ret = ret.filter(*filters)
        ret = ret.offset(skip)
        if limit is not None:
            ret = ret.limit(limit)
        if order_by is not None:
            ret.order_by(order_by)
        return await session.stream_scalars(ret)

from .history import *
from .page import *

__all__ = tuple()
