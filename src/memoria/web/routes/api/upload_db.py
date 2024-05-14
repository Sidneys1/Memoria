from datetime import datetime, timedelta
from logging import getLogger
from tempfile import NamedTemporaryFile
from typing import TYPE_CHECKING

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

    from ....allowlist import AllowlistEntry as Ale
    from ....model.history_db import ChromiumPlace, MozPlace

    acls: dict[str, list[Ale]] = {}

    async with aiofiles.open(SETTINGS.allowlist) as allowlist, aiofiles.open(SETTINGS.denylist) as denylist:
        await Ale.load_acls_async(acls, allowlist, True)
        await Ale.load_acls_async(acls, denylist, False)

    visits: 'list[ImportedHistory]' = []
    filtered = 0
    too_soon = 0
    total = 0
    try:
        _LOG.debug("Trying as Mozilla...")
        async for place in MozPlace.from_sqlite_file(tempfile.name):
            if place.url is None:
                continue
            total += 1
            if Ale.check_parse_acls(place.url, urlparse(place.url), acls) != True:
                filtered += 1
                continue
            if await History.find_one(
                    session, History.url == place.url, History.last_scrape >= before_date) is not None:
                too_soon += 1
                continue
            visits.append(place)
    except ValueError as ex:
        _LOG.warning("Failed to interpret upload as a Firefox `places.sqlite` file: %s", str(ex))
    else:
        _LOG.debug("Adding background task...")
        background.add_task(_do_download, visits)
        _LOG.debug("Returning...")
        return {'count': len(visits), 'total': total, 'type': 'Mozilla'}

    visits = []
    filtered = 0
    too_soon = 0
    total = 0
    try:
        _LOG.debug("Trying as Chromium...")
        async for place in ChromiumPlace.from_sqlite_file(tempfile.name):
            if place.url is None:
                continue
            total += 1
            if Ale.check_parse_acls(place.url, urlparse(place.url), acls) != True:
                filtered += 1
                continue
            if await History.find_one(
                    session, History.url == place.url, History.last_scrape >= before_date) is not None:
                too_soon += 1
                continue
            visits.append(place)
    except ValueError as ex:
        _LOG.warning("Failed to interpret upload as a Chromium `History` file: %s", str(ex))
    else:
        _LOG.debug("Adding background task...")
        background.add_task(_do_download, visits)
        _LOG.debug("Returning...")
        return {'count': len(visits), 'total': total, 'filtered': filtered, 'too_soon': too_soon, 'type': 'Chromium'}

    _LOG.error("Failed to interpret upload as a known browser history database.")
    raise HTTPException(422, "Failed to interpret upload as a known browser history database.")


__all__ = tuple()
