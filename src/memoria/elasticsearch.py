from typing import TYPE_CHECKING
from logging import getLogger

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch

_LOG = getLogger(__spec__.name)

PAGES_INDEX_KWARGS = {
    'settings': {
        'similarity': {
            "scripted_tfidf": {
                "type": "scripted",
                "weight_script": {
                    "source":
                    "double idf = Math.log((field.docCount+1.0)/(term.docFreq+1.0)) + 1.0; return query.boost * idf;"
                },
                "script": {
                    "source":
                    "double tf = Math.sqrt(doc.freq); double norm = 1/Math.sqrt(doc.length); return weight * tf * norm;"
                }
            }
        },
        'analysis': {
            'analyzer': {
                'fulltext_analyzer': {
                    'type': 'custom',
                    'tokenizer': 'whitespace',
                    'filter': ['lowercase', 'type_as_payload', 'stop'],
                    'ignore_case': True
                },
                "my_english_analyzer": {
                    "type": "standard",
                    "stopwords": "_english_"
                }
            }
        }
    },
    'mappings': {
        "properties": {
            "text": {
                "type": "text",
                "similarity": "scripted_tfidf",
                'term_vector': 'with_offsets',
                'store': True,
                'analyzer': 'my_english_analyzer'
            },
            "preview": {
                "type": "text",
                'index': False
            }
        }
    }
}


async def check_es_indexes(es: 'AsyncElasticsearch') -> None:
    _LOG.info('Checking Elasticsearch indexes...')

    # if not await es.indices.exists(index='history'):
    #     _LOG.info('Creating `history` index...')
    #     await es.indices.create(index='history')

    if not await es.indices.exists(index='pages'):
        _LOG.info('Creating `pages` index...')
        await es.indices.create(index='pages', **PAGES_INDEX_KWARGS)
