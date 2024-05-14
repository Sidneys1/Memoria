from typing import Annotated, Any

from fastapi import Depends
from fasthx import JinjaContext

from ....logic.history import get_history
from ....model.history import History
from ...db_dependencies import get_session
from .. import HX
from . import API

_RESPONSES = {200: {'content': {'text/html': {}}}}


@API.get("/history", response_model=list[History], responses=_RESPONSES)
@HX.hx('history_items.html.j2', make_context=JinjaContext.unpack_result_with_route_context)
async def api_history(session: Annotated['Any', Depends(get_session)], skip: int = 0, limit: int | None = None):
    return [x async for x in await get_history(session, skip=skip, limit=limit)]


__all__ = tuple()
