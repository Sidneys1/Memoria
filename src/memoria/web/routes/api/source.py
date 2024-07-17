from fasthx import JinjaContext

from ....logic.source import Source, get_sources
from ...db_dependencies import SqlSession
from .. import HX
from . import API

_RESPONSES = {200: {'content': {'text/html': {}}}}


@API.get("/sources", response_model=list[Source], responses=_RESPONSES)
@HX.hx('sources_items.html.j2', make_context=JinjaContext.unpack_result_with_route_context)
async def api_sources(session: SqlSession, skip: int = 0, limit: int | None = None):
    return [Source.model_validate(x) async for x in await get_sources(session, skip=skip, limit=limit)]


@API.delete("/sources/{id}")
@HX.hx('blank.html.j2')
async def api_delete_source(session: SqlSession, id: int):
    from ....model.orm.configured_source import ConfiguredSource
    async with session.begin():
        await session.delete(await ConfiguredSource.find_one(session, ConfiguredSource.id == id))


__all__ = tuple()
