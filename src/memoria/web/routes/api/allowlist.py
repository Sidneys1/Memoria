from fastapi import Form
from fasthx import JinjaContext

from ....logic.allowlist import AllowlistHost, get_allowlist
from ...db_dependencies import SqlSession
from .. import HX
from . import API

_RESPONSES = {200: {'content': {'text/html': {}}}}


@API.get("/allowlist", response_model=list[AllowlistHost], responses=_RESPONSES)
@HX.hx('allowlist_items.html.j2', make_context=JinjaContext.unpack_result_with_route_context)
async def api_allowlist(session: SqlSession, skip: int = 0, limit: int | None = None):
    return [x async for x in get_allowlist(session, skip=skip, limit=limit)]


@API.post("/allowlist", response_model=AllowlistHost)
@HX.hx('allowlist_item.html.j2')
async def api_new_allowlist(session: SqlSession, hostname: str = Form()):
    from ....model.orm.allowlist import AllowlistHost as OrmHost
    host = OrmHost(hostname=hostname, allowed=True)
    async with session.begin():
        session.add(host)
    return host


@API.delete("/allowlist/{hostname}")
@HX.hx('blank.html.j2')
async def api_delete_allowlist(session: SqlSession, hostname: str):
    from ....model.orm.allowlist import AllowlistHost as OrmHost
    async with session.begin():
        await session.delete(await OrmHost.find_one(session, OrmHost.hostname == hostname, OrmHost.allowed == True))


__all__ = tuple()
