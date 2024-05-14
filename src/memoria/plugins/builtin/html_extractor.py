from logging import getLogger
from urllib.parse import urljoin

from bs4 import BeautifulSoup, PageElement, Tag

from ..extractor import Extractor, Result

ALLOWED_META = ('author', 'description')


class HtmlExtractor(Extractor):
    __log = getLogger(__spec__.name + '.HtmlExtractor')

    accept = {'text/html', 'application/x-beautifulsoup'}

    @staticmethod
    def _allowed_meta(meta: PageElement) -> bool:
        return 'name' in meta.attrs and 'content' in meta.attrs and meta.attrs['name'] in ALLOWED_META

    async def extract(self, input_: Result) -> Result:
        bs: Tag
        parent: BeautifulSoup

        match input_.content_type, input_.content:
            case 'text/html', (str() | bytes()):
                self.__log.debug('From text/html...')
                bs = BeautifulSoup(input_.content, from_encoding=input_.encoding, features="html.parser")
                parent = bs
            case 'application/x-beautifulsoup', Tag():
                self.__log.debug('From BS4...')
                bs = input_.content

                # Find the oldest BeautifulSoup
                parent = bs
                cur = input_
                i = 0
                while cur.original is not None:
                    i += 1
                    self.__log.debug('Searching parents %d levels up...', i)
                    cur = cur.original
                    if cur.content_type == 'application/x-beautifulsoup' and isinstance(cur.content, Tag):
                        parent = cur.content
                        self.__log.debug('Parent is a previous BS4...')
                    elif cur.content_type == 'text/html' and isinstance(cur.content, (str, bytes)):
                        parent = BeautifulSoup(cur.content, from_encoding=cur.encoding, features="html.parser")
                        self.__log.debug('Parent is now text/html...')
                    else:
                        self.__log.debug("Can't work with `%s`...", cur.content_type)
            case _:
                raise ValueError(f"This plugin does not accept `{input_.content_type}`, only `text/html` and `application/x-beautifulsoup` is supported.")

        attrs = dict(**input_.meta)
        attrs.update({
            meta.attrs['name']: meta.attrs['content']
            for meta in parent.find_all('meta') if self._allowed_meta(meta)
        })
        if (elem := parent.find('title')) is not None:
            attrs['title'] = elem.text

        # for link in parent.find_all('link'):
        #     self.__log.debug("Found a <link rel=\"%s\" ...>...", link.attrs['rel'])

        if (elem := parent.find('link', attrs={'rel': 'icon'})) is not None:
            self.__log.debug("Found <link rel=\"icon\" href=\"%s\"> (%s, %s)", elem.attrs['href'], type(input_.url).__name__, type(elem.attrs['href']).__name__)
            attrs['favicon'] = urljoin(input_.url, elem.attrs['href'])
        else:
            self.__log.debug("No <link rel=\"icon\" ...>")

        return Result(request_url=input_.request_url, url=input_.url, content=bs.get_text(separator=' ', strip=True), content_type='text/plain', encoding=None, meta=attrs, original=input_)
