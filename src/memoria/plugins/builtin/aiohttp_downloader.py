from logging import getLogger
from typing import TYPE_CHECKING, Any, Coroutine, Self

if TYPE_CHECKING:
    from aiohttp import ClientSession

from ..base import Result
from ..downloader import Downloader

HEADERS = {
    'User-Agent':
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.100 Safari/537.36'
}


class AiohttpDownloader(Downloader):
    _session: 'ClientSession'
    __log = getLogger(__spec__.name + '.AiohttpDownloader')

    content_types = {'text/html'}

    @classmethod
    def install_extra(cls) -> bool:
        what = '???'
        try:
            try:
                import aiohttp
            except ImportError:
                cls.__log.warning("Package `selenium` not installed. Installing with `pip`...")
                what = 'aiohttp'
                import subprocess
                from sys import executable
                subprocess.check_call([executable, '-m', 'pip', 'install', '--no-cache-dir', 'aiohttp[speedups]'])
                import aiohttp
        except:
            cls.__log.critical("Failed to install `%s`, aborting...", what)
            return False

        return True

    def __init__(self) -> None:
        from aiohttp import ClientSession, TCPConnector
        self._session = ClientSession(connector=TCPConnector(force_close=True, enable_cleanup_closed=True),
                                      headers=HEADERS)

    async def __aenter__(self) -> Coroutine[Any, Any, Self]:
        await self._session.__aenter__()
        return self

    async def __aexit__(self, *args) -> None:
        """Raise any exception triggered within the runtime context."""
        await self._session.__aexit__(*args)
        return None

    async def download(self, url: str, want_content_types: set[str]) -> Result | None:
        if 'text/html' not in want_content_types:
            raise ValueError(
                f"This plugin does not produce `{content_type}`! Supported Content-Types are `{'`, `'.join(self.content_types)}`."
            )

        from aiohttp import ClientError, TooManyRedirects
        try:
            async with self._session.get(url) as response:
                if response.status != 200:
                    self.__log.warning("Got HTTP %d from `%s`.", response.status, url)
                    return None
                content_type: str = response.content_type
                if not content_type.startswith('text/html'):
                    self.__log.warning("Got non-HTML Content-Type `%s` from `%s`.", content_type, url)
                    return None
                return Result(request_url=url,
                              url=str(response.url),
                              content=await response.read(),
                              content_type='text/html',
                              encoding=response.get_encoding())
        except TooManyRedirects:
            self.__log.error("`%s` redirected too many times.", url)
            return None
        except ClientError:
            self.__log.exception("Unhandled exception while downloading `%s`:", url)
            return None
