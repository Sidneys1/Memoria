from datetime import UTC, datetime
from io import TextIOBase
from logging import getLogger
from os import SEEK_END
from typing import TYPE_CHECKING, Iterator
from urllib.parse import ParseResult, urlparse

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch

from pydantic import ValidationError

from .allowlist import AllowlistEntry as Ale
from .util import *
from .downloader import do_download
from .model.imported_history import ImportedMozillaHistory

_LOG = getLogger(__spec__.name)


def _ask_missing_acl(ns, parse: ParseResult, acls: dict[str, list[Ale]]) -> bool:
    parts = [
        GREY(parse.scheme + '://'),
        RED(parse.netloc),
        ORANGE(parse.path),
        YELLOW(parse.params),
        GREEN(parse.query),
        BLUE(parse.fragment)
    ]
    print("The following URL did not match any existing allowlist if denylist entries:\n    ",
          GREY(parse.scheme),
          '://',
          RED(parse.netloc),
          ORANGE(parse.path),
          YELLOW(parse.params),
          sep='')
    choice = input("No allowlist or denylist entry matches this URL exactly. Do you want to:\n"
                   f" 1) Add a new rule to the {GREEN}allowlist{DEFAULT_COLOR};\n"
                   f" 2) Add a new rule to the {RED}denylist{DEFAULT_COLOR}; or\n"
                   " 3) Skip for now?\n")
    if choice == '3':
        return False

    if choice not in ('1', '2'):
        raise RuntimeError()

    try:
        rule = input(
            ("Please enter a blank line to add {3}{4}{0}, or type a list entry of form `HOST [RULE ...]`. "
             "Optional RULEs can be a {2}path{0} prefix beginning with `{1}/{0}` "
             "(e.g.: {1}/login{0}), or a regular expression matching any part of the {2}path{0} "
             "(e.g.: {1}r^/a${0} would match `/a`, but not `/a/`).\n> {1}").format(DEFAULT_COLOR, CYAN, ORANGE, RED,
                                                                                   parse.netloc))
    finally:
        print(DEFAULT_COLOR)

    allow = choice == '1'
    file = ns.allowlist if allow else ns.denylist
    if not rule:
        entry = Ale(parse.netloc, allow)
    else:
        entry = Ale.from_file(allow, rule.strip())

    if entry.host not in acls:
        acls[entry.host] = [entry]
    else:
        acls[entry.host].append(entry)

    file.write(entry.dumps() + '\n')
    file.flush()


def _load_mozilla_history(stream: TextIOBase) -> Iterator[ImportedMozillaHistory]:
    import ijson

    count = 0
    most_recent = datetime.fromtimestamp(0, tz=UTC)
    for parse in ijson.items(stream, 'item'):
        try:
            item = ImportedMozillaHistory(**parse)
            yield item
            count += 1

            if (this_most_recent := item.last_visit) > most_recent:
                most_recent = this_most_recent
        except ValidationError as e:
            _LOG.exception("Failed to load history item.")

    if count > 0:
        _LOG.info(f"Loaded {count:,} history items. Most recent: {most_recent.isoformat()}")


async def do_upload(ns, es: 'AsyncElasticsearch') -> None:
    acls: dict[str, list[Ale]] = {}

    Ale._load_acls(acls, ns.allowlist, True)
    ns.allowlist.seek(0, SEEK_END)
    Ale._load_acls(acls, ns.denylist, False)
    ns.denylist.seek(0, SEEK_END)

    todo = []
    with ns.input.open() as stream:
        for i, history in enumerate(_load_mozilla_history(stream), start=1):
            if await es.exists(index='history', id=history.id):
                # _LOG.debug("`%s` already exists.", history.id)
                continue

            parse = urlparse(history.url)

            decision = Ale._check_parse_acls(parse, acls)

            if decision is None:
                print(f"- #{i:,}: {history.url}")
                if not _ask_missing_acl(ns, parse, acls):
                    continue
            elif not decision:
                _LOG.debug(f"`{parse.netloc}` is {RED}denylisted{DEFAULT_COLOR} ({history.url}).")
                continue
            _LOG.debug(f"`{parse.netloc}` is {GREEN}allowlisted{DEFAULT_COLOR} ({history.url}).")

            todo.append(history)

    if input(f'Download {len(todo):,} items? [yN] ').lower() == 'y':
        await do_download(todo)
