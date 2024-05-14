import re
from logging import getLogger
from typing import Any
from copy import deepcopy

from bs4 import BeautifulSoup, Comment

from memoria.plugins.base import Result

from ..filter import Filter

_LOG = getLogger(__spec__.name)


def find_one_of(soup: BeautifulSoup, element: str) -> BeautifulSoup:
    _LOG.debug('looking for %s', element)
    res: list[BeautifulSoup]
    if (res := soup.find_all(element, limit=2)) and len(res) == 1:
        _LOG.debug("Found a singular <%s> element. Scoping.", element)
        return res[0]
    return soup


def clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    _LOG.debug('cleaning HTML')
    [comment.extract() for comment in soup.findAll(string=lambda text: isinstance(text, Comment))]
    [button.extract() for button in soup.find_all('a', {'role': 'button'})]
    [match.extract() for match in soup.find_all({'form', 'input', 'nav'})]
    [match.extract() for match in soup.find_all(class_='noprint')]

    for header in soup(['header', 'script', 'style']):
        header.decompose()

    ret = soup
    for element in ('main', 'article'):
        ret = find_one_of(ret, element)

    if (id_elem := ret.find_all(attrs={'id': re.compile('^content$', re.I)}, limit=2)) and len(id_elem) == 1:
        _LOG.debug("Found a <... id='content'> element. Scoping.")
        soup = id_elem[0]

    return ret


class HtmlContentFinder(Filter):
    __log = getLogger(__spec__.name + '.HtmlContentFinder')

    accept = {'text/html', 'application/x-beautifulsoup'}
    content_types = {'application/x-beautifulsoup'}

    async def transform(self, input_: Result, want_content_types: set[str]) -> Result:
        if 'application/x-beautifulsoup' not in want_content_types:
            raise ValueError(
                f"This plugin cannot produce [`{'`, `'.join(want_content_types)}`], only `application/x-beautifulsoup`."
            )

        bs: BeautifulSoup

        match input_.content_type, input_.content:
            case 'text/html', (str() | bytes()):
                bs = BeautifulSoup(input_.content, from_encoding=input_.encoding, features="html.parser")
            case 'application/x-beautifulsoup', BeautifulSoup():
                bs = input_.content
            case _:
                raise ValueError(
                    f"This plugin does not accept `{input_.content_type}`, only `text/html` and `application/x-beautifulsoup`."
                )

        return Result(request_url=input_.request_url,
                      url=input_.url,
                      content=clean_html(deepcopy(bs)),
                      content_type='application/x-beautifulsoup',
                      encoding=None,
                      meta=input_.meta,
                      original=input_)
