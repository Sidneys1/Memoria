import asyncio
import atexit
import concurrent.futures
import multiprocessing as mp
from datetime import datetime
from hashlib import sha256
from logging import Logger, getLogger
from queue import Empty
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from elasticsearch import AsyncElasticsearch
    from sqlalchemy.ext.asyncio import AsyncSession
    from threading import Event
    from queue import Queue

from .model.imported_history import ImportedHistory
from .plugins import PluginProcessor, PluginSuite, Result
from .settings import SETTINGS

_LOG = getLogger(__spec__.name)


async def _create_history_entry(session: 'AsyncSession', history: ImportedHistory, last_scrape: datetime|None) -> None:
    from .model.orm.history import History as SqlHistory
    async with session.begin():
        if (existing := await SqlHistory.find_one(session, SqlHistory.url == history.url)) is not None:
            if existing.last_visit != history.last_visit:
                existing.last_visit = history.last_visit
            if last_scrape is not None:
                existing.last_scrape = last_scrape
            await session.commit()
            return
        session.add(SqlHistory(last_scrape=last_scrape, **history.model_dump(include={'url', 'title', 'last_visit'})))


async def process_one(log: Logger, es: 'AsyncElasticsearch', sql_session: 'AsyncSession', processor: PluginProcessor,
                      history: ImportedHistory) -> None:
    log.debug('Attempting to download `%s`', history.url)

    content_hash: str
    exists_called = False

    async def check_exists(result: Result):
        nonlocal exists_called
        nonlocal content_hash
        nonlocal history
        exists_called = True
        content: bytes
        if isinstance(result.content, str):
            content = result.content.encode()
        else:
            assert isinstance(result.content, bytes)
            content = result.content
        content_hash = sha256(content).hexdigest()
        if not await es.exists(index='pages', id=content_hash):
            return False
        await _create_history_entry(sql_session, history, datetime.now())
        log.debug("The content of `%s` has been downloaded before. Continuing.", history.url)
        return True

    result = await processor.process_one(history, check_exists)
    if result is None:
        if not exists_called:
            log.warning("The content of `%s` could not be downloaded.", history.url)
            await _create_history_entry(sql_session, history, None)
        return

    assert isinstance(result.content, str)

    await es.index(
        index='pages',
        id=content_hash,
        document={
            'url': history.url,
            'timestamp': datetime.now(),
            'text': result.content,
            'title': result.meta.get('title', history.title),
            # 'preview': ...
            **result.meta
        })

    log.info("`%s` has been archived.", history.url)
    await _create_history_entry(sql_session, history, datetime.now())


async def worker(log: Logger, queue: 'Queue[ImportedHistory]', no_more: 'Event', canceled: 'Event') -> None:
    from .db_clients import create_elasticsearch_client, create_sql_client
    processor = PluginSuite().create_processor()
    es = await create_elasticsearch_client(SETTINGS.elastic_host,
                                           basic_auth=(SETTINGS.elastic_user, SETTINGS.elastic_password))
    async with create_sql_client() as sql_session, es, processor:
        while not canceled.is_set():
            try:
                await process_one(log, es, sql_session, processor, queue.get(block=not no_more.is_set()))
            except Empty:
                if no_more.is_set():
                    return
                if canceled.is_set():
                    log.critical("Canceled!")
                    return
            except (asyncio.CancelledError, KeyboardInterrupt, GeneratorExit):
                log.critical("Canceled!")
                return
            except RuntimeError as ex:
                if ex.args[0] == "Event loop is closed":
                    log.critical("Event loop closed!")
                    return
                log.exception("Unhandled critical exception whille processing history item, cannot continue:")
                return
            except Exception:
                log.exception("Unhanded exception while processing history item:")
            except BaseException:
                log.exception("Unhandled critical exception whille processing history item, cannot continue:")
                return


def worker_main(log: int, queue: 'Queue[ImportedHistory]', no_more: 'Event', canceled: 'Event') -> None:
    asyncio.new_event_loop().run_until_complete(worker(getLogger(__spec__.name + f"<{log}>"), queue, no_more, canceled))


def _worker_done(future: asyncio.Future[None]) -> None:
    if future.cancelled():
        _LOG.warning("Executor process was canceled")
    elif (ex := future.exception()) is not None:
        _LOG.exception("Executor process raised exception: %s", str(ex), exc_info=ex)

def _setup_logging() -> None:
    import logging
    from . import MODULE_LOGGER
    from .util import ColorFormatter
    logger = MODULE_LOGGER
    logger.level = logging.DEBUG
    handler = logging.StreamHandler()
    handler.setLevel(logger.level)
    handler.setFormatter(ColorFormatter())
    logger.addHandler(handler)

async def do_download(todo: list[ImportedHistory]) -> None:
    num_workers = max(1, min(len(todo) // 2, SETTINGS.import_threads))
    _LOG.info(f'Downloading {len(todo):,} URLs across {num_workers} workers...')

    context = mp.get_context()
    total = len(todo)

    with mp.Manager() as manager, concurrent.futures.ProcessPoolExecutor(max_workers=num_workers, mp_context=context, initializer=_setup_logging) as pool:
        queue: 'Queue[ImportedHistory]' = manager.Queue()
        no_more = manager.Event()
        canceled = manager.Event()

        loop = asyncio.get_running_loop()
        _LOG.debug("Creating executors.")
        futures = [
            loop.run_in_executor(pool, worker_main, i+1, queue, no_more, canceled)
            for i in range(min(SETTINGS.import_threads, len(todo)))
        ]
        for f in futures:
            f.add_done_callback(_worker_done)

        async def stop_all() -> list:
            nonlocal futures
            canceled.set()
            # Give it a second...
            _, futures = await asyncio.wait(futures, timeout=1)

            if not futures:
                return

            for x in futures:
                # Force it...
                x.cancel()

            _, futures = await asyncio.wait(futures, timeout=1)
            if futures:
                _LOG.critical("Trying to shut down, but there are still %d workers that haven't stopped.", len(futures))
            return futures

        @atexit.register
        def kill_mp_children():
            future = asyncio.wait_for(stop_all(), timeout=2)
            try:
                children = loop.run_until_complete(future)
                if not children:
                    return
            except asyncio.TimeoutError:
                _LOG.debug("Failed to cancel al futures in time")

            for p in mp.active_children():
                p.join(timeout=0.5)
                if p.exitcode is not None:
                    continue
                _LOG.warning("Worker process failed to exit in a timely fashion! Killing...")
                p.kill()

        for t in todo:
            queue.put(t)
        no_more.set()

        _LOG.debug("Queue filled. Waiting for executors to finish.")

        try:
            last = total
            while futures:
                _, futures = await asyncio.wait(futures, timeout=1)

                size = queue.qsize()
                if size != last:
                    last = size
                    _LOG.info("Queue has %d of %d (%.02f%%) items remaining", size, total, size / total * 100)
        except asyncio.CancelledError:
            await stop_all()
