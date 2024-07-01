from typing import Annotated, Any

from fastapi import Depends, Form
from fasthx import JinjaContext

from ....logic.allowlist import AllowlistHost, get_denylist
from ...db_dependencies import SqlSession
from .. import HX
from . import API

_RESPONSES = {200: {'content': {'text/html': {}}}}


@API.get("/denylist", response_model=list[AllowlistHost], responses=_RESPONSES)
@HX.hx('denylist_items.html.j2', make_context=JinjaContext.unpack_result_with_route_context)
async def api_denylist(session: SqlSession, skip: int = 0, limit: int | None = None):
    return [x async for x in await get_denylist(session, skip=skip, limit=limit)]


@API.post("/denylist", response_model=AllowlistHost)
@HX.hx('denylist_item.html.j2')
async def api_new_denylist(session: SqlSession, hostname: str = Form()):
    from ....model.orm.allowlist import AllowlistHost as OrmHost
    host = OrmHost(hostname=hostname, allowed=False)
    async with session.begin():
        session.add(host)
    return host


@API.delete("/denylist/{hostname}")
@HX.hx('blank.html.j2')
async def api_delete_denylist(session: SqlSession, hostname: str):
    from ....model.orm.allowlist import AllowlistHost as OrmHost
    async with session.begin():
        await session.delete(await OrmHost.find_one(session, OrmHost.hostname == hostname, OrmHost.allowed == False))


__all__ = tuple()
