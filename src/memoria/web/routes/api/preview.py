from fastapi.responses import HTMLResponse

from ....logic.preview import get_preview
from ...db_dependencies import Elasticsearch
from . import API, ContentType, HtmxHeader

_RESPONSES = {
    200: {
        'content': {
            'text/html': {
                'example': '<div>Content...</div>'
            },
            'application/json': {
                'example': '<div>Content...</div>'
            }
        }
    }
}


@API.get("/preview/{item_id}", response_model=str, responses=_RESPONSES)
async def api_search(es: Elasticsearch, item_id: str, accept: ContentType, hx_request: HtmxHeader = None):
    preview = await get_preview(es, item_id)
    if hx_request is not None or accept == 'text/html':
        return HTMLResponse(preview)
    return preview


__all__ = tuple()
