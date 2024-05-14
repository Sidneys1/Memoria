from typing import Annotated
from urllib.parse import quote_plus

from fastapi import Form, Response

from ....logic.search import search
from ....model.search_result import Result
from ...db_dependencies import Elasticsearch
from .. import HX
from . import API, HtmxHeader

_RESPONSES = {
    200: {
        'content': {
            'text/html': {
                'example': '<ul><li>...</li></ul>'
            },
        }
    }
}


@API.post("/search", response_model=list[Result], responses=_RESPONSES)
@HX.hx('results.html.j2')
async def api_search(response: Response,
                     es: Elasticsearch,
                     query: Annotated[str, Form()],
                     hx_request: HtmxHeader = None) -> list[Result]:
    if hx_request is not None:
        response.headers['HX-Push-Url'] = '?q=' + quote_plus(query)
    return [x async for x in search(es, query)]


__all__ = tuple()
