from logging import getLogger
from functools import reduce
import re

from bs4 import BeautifulSoup, Comment

_LOG = getLogger(__spec__.name)

def _find_one_of(soup: BeautifulSoup, element: str) -> BeautifulSoup:
    _LOG.debug('looking for %s', element)
    res: list[BeautifulSoup]
    if (res := soup.find_all(element, limit=2)) and len(res) == 1:
        _LOG.debug("Found a singular <%s> element. Scoping.", element)
        return res[0]
    return soup

def clean_html(soup: BeautifulSoup) -> BeautifulSoup:
    _LOG.debug('cleaning HTML')
    soup = soup.__copy__()
    [comment.extract() for comment in soup.findAll(string=lambda text: isinstance(text, Comment))]
    [button.extract() for button in soup.find_all('a', {'role': 'button'})]
    [match.extract() for match in soup.find_all({'form', 'input', 'nav'})]
    [match.extract() for match in soup.find_all(class_='noprint')]

    for header in soup(['header', 'script', 'style']):
        header.decompose()

    ret = soup
    for element in ('main', 'article'):
        ret = _find_one_of(ret, element)

    if (id_elem := ret.find_all(attrs={'id': re.compile('^content$', re.I)}, limit=2)) and len(id_elem) == 1:
        _LOG.debug("Found a <... id='content'> element. Scoping.")
        soup = id_elem[0]

    return ret
