from typing import TYPE_CHECKING, AsyncGenerator, Coroutine, AsyncIterable

from ..model.allowlist import AllowlistHost
from ..model.orm.allowlist import AllowlistHost as OrmHost

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


async def get_allowlist(session: 'AsyncSession', skip: int = 0, limit: int|None = None) -> AsyncGenerator[AllowlistHost, None]:
    async for host in await OrmHost.find_all(session, OrmHost.allowed == True, skip=skip, limit=limit,  order_by=OrmHost.id.desc()):
        yield AllowlistHost(id=host.id, hostname=host.hostname, rules=list(await host.awaitable_attrs.rules))


def get_denylist(session: 'AsyncSession', skip: int = 0, limit: int|None = None) -> Coroutine[None, None, AsyncIterable[OrmHost]]:
    return OrmHost.find_all(session, OrmHost.allowed == False, skip=skip, limit=limit, order_by=OrmHost.id.desc())
