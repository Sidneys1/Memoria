from ...model.search_result import Result
from .. import APP
from . import HX


@APP.get('/')
@HX.page('index.html.j2')
async def index(q: str|None = None) -> list[Result]:
    if q is None:
        return []
    from ...logic.search import search
    from ..db_dependencies import get_elasticsearch
    return [x async for x in search(await get_elasticsearch(), q)]


__all__ = tuple()
