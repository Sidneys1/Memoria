async def _main():
    from logging import DEBUG, INFO, basicConfig, getLogger

    basicConfig(level=DEBUG)
    log = getLogger()
    getLogger('aiosqlite').setLevel(INFO)

    from .db_clients import create_sql_client
    from .plugins._allowlist_manager import AllowlistPluginManager, AllowlistRule
    from .plugins._plugin_suite import PluginSuite

    async with create_sql_client() as client:
        # async with client.begin():
        #     client.add(AllowlistHost(hostname='stackoverflow.com', allowed=True))

        # async with client.begin():
        #     stackoverflow = await AllowlistHost.find_one(client, AllowlistHost.hostname == 'stackoverflow.com')
        #     print(f'Stackoverflow: {stackoverflow!r}')

            # client.add(dbAllowlistRule(host=stackoverflow, plugin_id='Regex', value=r'https?://[^/]+/$'))
            # await client.delete(await dbAllowlistRule.find_one(client, dbAllowlistRule.id == 3))
            # await client.delete(await dbAllowlistRule.find_one(client, dbAllowlistRule.id == 4))

        # async for host in await AllowlistHost.find_all(client):
        #     print(host.id, host.hostname, host.allowed)
        #     for rule in await host.awaitable_attrs.rules:
        #         print(f"- {rule.id} {rule.plugin_id} {rule.value!r}")

        suite = PluginSuite()
        manager = AllowlistPluginManager([x for x in suite._plugins.values() if issubclass(x, AllowlistRule)])
        urls = [
            'https://stackoverflow.com/', 'https://stackoverflow.com/about', 'https://stackoverflow.com/q/12345',
            'https://www.stackoverflow.com/question/12345'
        ]

        if True:
            from .db_clients import get_sql_client
            from .model.orm.allowlist import AllowlistRule as dbAllowlistRule
            client = get_sql_client()
            print("Rules:")
            async for rule in await dbAllowlistRule.find_all(client):
                print(f" - <{(await rule.awaitable_attrs.host).hostname}> [{rule.plugin_id}]: {rule.value!r}")

        async def gen_urls():
            from urllib.parse import urlparse
            for url in urls:
                print(f"Generated `{url}`")
                yield url, urlparse(url)
        async with manager:
            async for url in manager.process_rules(gen_urls()):
                print(f"\t{url}")




if __name__ == '__main__':
    import asyncio
    asyncio.run(_main())
