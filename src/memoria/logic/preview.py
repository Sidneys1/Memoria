from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch


async def get_preview(es: 'AsyncElasticsearch', id_: str) -> str:
    resp = await es.get(index='pages', id=id_, source_includes=('preview',))
    if not resp.get('found', False):
        raise LookupError("No page with that ID exists.")
    return resp['_source']['preview']

