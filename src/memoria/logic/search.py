from logging import getLogger

from ..model.search_result import Result

from urllib.parse import urlparse
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch

_LOG = getLogger(__spec__.name)


async def search(es: 'AsyncElasticsearch', query: str, size:int=25) -> AsyncGenerator[Result, None]:
    resp = await es.search(index='pages', query={'match': {'text': query}}, explain=True, size=size, source_includes=('_id','title','url','timestamp', 'author', 'favicon', 'description'))
    if 'hits' not in resp or 'hits' not in resp['hits'] or not isinstance(resp['hits']['hits'], list):
        return

    for hit in resp['hits']['hits']:
        source = hit['_source']
        kwargs = {
            '_id': hit['_id'],
            'score': hit['_score'],
            'basename': source['basename'] if 'basename' in source else urlparse(source['url']).hostname,
            'explanation': {},
            **hit['_source']
        }

        if hit['_explanation']['description'] == 'sum of:':
            for detail in hit['_explanation']['details']:
                kwargs['explanation'][detail['description'][12:].split(' in ', maxsplit=1)[0]] = detail['value']  # / resp['hits']['max_score']

        yield Result(**kwargs)

