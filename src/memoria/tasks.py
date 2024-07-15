import asyncio
from contextlib import asynccontextmanager

from rocketry import Rocketry
from multiprocessing import Process, Event, Manager


APP = Rocketry(execution='async')


async def _main() -> None:
    from .plugins._source_manager import SourcePluginManager
    async with SourcePluginManager() as manager:
        manager.start()


SUBPROCESS: Process = Process(target=lambda: asyncio.run(_main()))
SUBPROCESS.daemon = True


@asynccontextmanager
async def tasks_lifecycle():
    SUBPROCESS.start()
    yield
    SUBPROCESS.kill()  # TODO: .join()
    SUBPROCESS = None  # type: ignore
