import asyncio
from logging import basicConfig, DEBUG, INFO

class importer:
    async def add_many(self, items) -> None:
        """"""
        async for x in items:
            # print("\t", x, sep='')
            print('.', end='', flush=True)
        print()

    async def add(self, item) -> None:
        """"""

    async def flush(self) -> None:
        """"""

async def main() -> None:
    from memoria.model.orm.configured_source import ConfiguredSource
    from memoria.plugins import PluginSchedule
    from memoria.plugins._source_manager import SourcePluginManager
    from memoria.db_clients import create_sql_client
    from memoria.plugins.source import PluginSchedule

    basicConfig(level=INFO)

    async with create_sql_client() as session:
        found: ConfiguredSource = await ConfiguredSource.find_one(session, ConfiguredSource.id == 1)  # type: ignore
        # found.display_name = 'Firefox Sync (<code>sidneys1@live.com</code>)'
        found.schedule = PluginSchedule.Scheduled.value
        found.schedule_value = '0 0 * * 0'
        # await session.delete(found)

        # new = ConfiguredSource(plugin_id='memoria.plugins.builtin.firefox_sync_client_source:FirefoxSyncClientSource', display_name='Firefox Sync: <samp>sidneys1@live.com</samp>', config='{}')
        # session.add(new)
        await session.commit()

        async for x in await ConfiguredSource.find_all(session):
            print(x.id, x.plugin_id, x.display_name, x.config, x.schedule, x.schedule_value, x.enabled, sep=', ')

    # async with SourcePluginManager() as manager:
    #     print(manager._instances)
    #     print(manager._config)
    #     print(manager._schedules)


    # plugin_id: str = None  # type: ignore
    # plugin_type: type[Source] = None  # type: ignore
    # for pid, plugin in suite.get_plugins_of_type(Source):
    #     # print(plugin.__name__, ','.join(x.name for x in plugin.SUPPORTED_SCHEDULES))
    #     plugin_type = plugin
    #     plugin_id = pid

    # config: JsonValue = None



    # print("Before 'with'")
    # async with plugin_type(config) as plugin:
    #     return
    #     i = importer()
    #     print("Before 'run'")
    #     await plugin.run(i)
    #     print("After 'run'")
    # print("After 'with'")

if __name__ == '__main__':
    asyncio.run(main())
