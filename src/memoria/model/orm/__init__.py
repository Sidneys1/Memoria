from typing import TYPE_CHECKING, Any, AsyncIterable, Self, Iterable

from sqlalchemy import Column as Col
from sqlalchemy import select, exists
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncAttrs, AsyncSession
from sqlalchemy.orm import DeclarativeBase, load_only

if TYPE_CHECKING:
    from sqlalchemy.orm.strategy_options import _AttrType

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
    async def find_one(cls, session: AsyncSession, filter_, *filters,
                       attrs: Iterable['_AttrType']|None = None) -> Self | None:
        try:
            ret = select(cls).filter(filter_, *filters)
            if attrs is not None:
                ret.options(load_only(*attrs))
            return (await session.execute(ret)).scalars().one()
        except NoResultFound:
            return None

    @classmethod
    async def exists(cls, session: AsyncSession, filter_, *filters) -> bool:
        return (await session.execute(exists(select(cls).filter(filter_, *filters)).select())).scalar()  # type: ignore

    @classmethod
    async def find_all(cls,
                       session: AsyncSession,
                       *filters,
                       attrs: Iterable['_AttrType']|None = None,
                       order_by: Any | None = None,
                       skip: int = 0,
                       limit: int | None = None) -> AsyncIterable[Self]:
        ret = select(cls)
        if filters:
            ret = ret.filter(*filters)
        ret = ret.offset(skip)
        if order_by is not None:
            ret = ret.order_by(order_by)
        if limit is not None:
            ret = ret.limit(limit)
        if attrs is not None:
            ret.options(load_only(*attrs))
        return await session.stream_scalars(ret)

from .history import *
from .page import *
from .allowlist import *

__all__ = tuple()
