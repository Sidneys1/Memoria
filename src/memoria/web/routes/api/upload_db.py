from datetime import datetime, timedelta
from logging import getLogger
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING, AsyncGenerator
from pathlib import Path

import aiofiles
from fastapi import BackgroundTasks, HTTPException, UploadFile

from ....model.orm.history import History
from ....settings import SETTINGS
from ...db_dependencies import SqlSession
from .. import HX
from . import API

if TYPE_CHECKING:

    from ....model.imported_history import ImportedHistory

CHUNK_SIZE = 1024 * 1024

_LOG = getLogger(__spec__.name)


async def _do_download(visits: list['ImportedHistory']) -> None:
    from ....downloader import do_download
    _LOG.info("Calling downloader")
    await do_download(visits)
    _LOG.info("Downloader done")


async def _gen_mozilla(sqlite_file: 'Path') -> AsyncGenerator['ImportedHistory', None]:
    from ....model.history_db import MozPlace
    async for place in MozPlace.from_sqlite_file(sqlite_file):
        if place.url is None:
            continue
        yield place


async def _gen_chromium(sqlite_file: 'Path') -> AsyncGenerator['ImportedHistory', None]:
    from ....model.history_db import ChromiumPlace
    async for place in ChromiumPlace.from_sqlite_file(sqlite_file):
        if place.url is None:
            continue
        yield place


def _gen_places(sqlite_file: 'Path') -> tuple[str, AsyncGenerator['ImportedHistory', None]] | None:
    _LOG.debug("Trying as Firefox...")
    try:
        generator = _gen_mozilla(sqlite_file)
    except ValueError as ex:
        _LOG.warning("Failed to interpret upload as a Firefox `places.sqlite` file: %s", str(ex))
    else:
        return 'Firefox', generator

    _LOG.debug("Trying as Chromium...")
    try:
        generator = _gen_chromium(sqlite_file)
    except ValueError as ex:
        _LOG.warning("Failed to interpret upload as a Chromium `History` file: %s", str(ex))
    else:
        return 'Chromium', generator


@API.post("/upload_db")
@HX.hx('upload.html.j2')
async def api_upload_db(file: UploadFile, background: BackgroundTasks, session: SqlSession):
    _LOG.debug("got upload!")
    tempfile = NamedTemporaryFile(delete_on_close=False)

    before_date = datetime.now() - timedelta(days=1.0)

    async with aiofiles.open(tempfile.name, 'wb') as out_file:
        while content := await file.read(CHUNK_SIZE):
            await out_file.write(content)

    from urllib.parse import urlparse

    if (ret := _gen_places(Path(tempfile.name))) is None:
        _LOG.error("Failed to interpret upload as a known browser history database.")
        raise HTTPException(422, "Failed to interpret upload as a known browser history database.")
    db_type, generator = ret

    visits: list['ImportedHistory'] = []
    blocked = 0
    too_soon = 0
    total = 0

    from ....plugins._plugin_suite import PluginSuite
    from ....plugins._allowlist_manager import AllowlistPluginManager, AllowlistRule

    suite = PluginSuite()
    manager = AllowlistPluginManager([x for x in suite._plugins.values() if issubclass(x, AllowlistRule)])

    async with manager:
        async def gen_places():
            nonlocal total
            nonlocal blocked
            nonlocal too_soon
            async for place in generator:
                total += 1
                parse = urlparse(place.url)

                if await manager.is_blocked(place.url, parse):
                    blocked += 1
                    continue

                if await History.find_one(
                        session, History.url == place.url, History.last_scrape >= before_date) is not None:
                    too_soon += 1
                    continue

                yield place, place.url, parse

            async for place in manager.process_rules(gen_places()):
                visits.append(place)

    _LOG.debug("Adding background task...")
    background.add_task(_do_download, visits)
    _LOG.debug("Returning...")
    filtered = (total - len(visits)) - too_soon
    return {'count': len(visits), 'total': total, 'filtered': filtered, 'too_soon': too_soon, 'type': db_type}


__all__ = tuple()
