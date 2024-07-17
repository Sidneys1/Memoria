from contextlib import AbstractAsyncContextManager, AsyncExitStack
from typing import TYPE_CHECKING, Self
from logging import getLogger

from ._plugin_suite import PluginSuite
from .source import Source
from . import  PluginSchedule

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from pydantic import JsonValue


class SourcePluginManager(AbstractAsyncContextManager):
    _LOG = getLogger(__spec__.name + '.SourcePluginManager')

    _stack: AsyncExitStack|None
    _instances: dict[int, Source]
    _config: dict[int, 'JsonValue']
    _schedules: dict[int, tuple[PluginSchedule, str]]

    def __init__(self) -> None:
        self._stack = None
        self._instances = {}
        self._config = {}
        self._schedules = {}

    def start(self) -> None:
        from ..tasks import APP
        from rocketry.conds import cron

        if self._stack is None:
            raise RuntimeError()

        for id, (schedule, value) in self._schedules.items():
            match schedule:
                case PluginSchedule.Intermittent:
                    APP.task(f'every {value} minutes', func=self._instances[id].run)
                case PluginSchedule.Scheduled:
                    APP.task(cron(value), func=self._instances[id].run)

        APP.run()


    async def _load(self, session: 'AsyncSession') -> None:
        type_map = {p.id: p.type for p in PluginSuite().get_plugins_of_type(Source)}

        from ..model.orm.configured_source import ConfiguredSource
        async for x in await ConfiguredSource.find_all(session):
            import json

            id: int = x.id  # type: ignore
            plugin_id: str = x.plugin_id  # type: ignore
            schedule: PluginSchedule = PluginSchedule(x.schedule)  # type: ignore
            schedule_value: str = x.schedule_value  # type: ignore
            enabled: bool = x.enabled  # type: ignore

            if not enabled:
                self._LOG.info("Skipping disabled Source plugin...")
                continue

            if plugin_id not in type_map:
                self._LOG.error("Configured Source plugin is of nonexistent type `%s`.", x.plugin_id)
                continue

            config: 'JsonValue' = None
            if x.config:  # type: ignore
                try:
                    config = json.loads(x.config)  # type: ignore
                except:
                    pass

            self._config[id] = config
            try:
                self._instances[id] = type_map[plugin_id][1](config)
            except ValueError:
                self._LOG.error("Configured Source plugin failed to load config.")
                continue

            self._schedules[id] = schedule, schedule_value

    async def __aenter__(self) -> Self:
        from ..db_clients import create_sql_client
        async with create_sql_client() as session:
            await self._load(session)

        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        for x in self._instances.values():
            await self._stack.enter_async_context(x)

        return self

    async def __aexit__(self, *args, **kwargs) -> bool | None:
        assert self._stack is not None
        await self._stack.__aexit__(*args, **kwargs)
        self._stack = None
        return False
