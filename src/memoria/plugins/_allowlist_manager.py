import re
from contextlib import AbstractAsyncContextManager, AsyncExitStack
from logging import getLogger
from typing import TYPE_CHECKING, AsyncGenerator, AsyncIterable, Generator, Self, TypeVar

if TYPE_CHECKING:
    from urllib.parse import ParseResult

from ..db_clients import create_sql_client
from ._ipv6_regex import IPV6_REGEX
from .allowlist import AllowlistRule, Hostname, InputItem

T = TypeVar('T')

class AllowlistPluginManager(AbstractAsyncContextManager):
    _LOG = getLogger(__module__ + '.AllowlistPluginManager')
    _rule_types: list[type[AllowlistRule]]
    _stack: None | AsyncExitStack
    _rule_instances: dict[str, AllowlistRule]
    _hostname_rule_cache: dict[Hostname, dict[str, set[str]] | None]
    _hostname_blocked_cache: dict[str, bool]

    _ipv4regex = re.compile(r"^(?:(?:25[0-5]|(?:2[0-4]|1[0-9]|[1-9]|)[0-9])(?:\.(?!$)|$)){4}$", flags=re.ASCII)
    _ipv6regex = re.compile(IPV6_REGEX, flags=re.ASCII)

    def __init__(self, rules: list[type[AllowlistRule]]) -> None:
        self._LOG.debug("Loaded allow/deny list rule types: [`%s`].", '`, `'.join(x.__name__ for x in rules))
        self._rule_types = rules
        self._stack = None
        self._rule_instances = {}

    async def __aenter__(self) -> Self:
        self._hostname_rule_cache = {}
        self._hostname_blocked_cache = {}
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()
        await self._stack.enter_async_context(create_sql_client())
        for rule_type in self._rule_types:
            rule = rule_type()
            self._rule_instances[rule_type.identifier] = rule
            await self._stack.enter_async_context(rule)
        return self

    async def __aexit__(self, *args, **kwargs) -> bool | None:
        del self._hostname_rule_cache
        del self._hostname_blocked_cache
        assert self._stack is not None
        ret = await self._stack.__aexit__(*args, **kwargs)
        self._stack = None
        self._rule_instances = {}
        return ret

    def _gen_hostnames(self, url: str, parse: 'ParseResult') -> Generator[InputItem, None, None]:
        hostname = parse.hostname
        if hostname is None:
            self._LOG.warning("Url `%s` has not hostname!", url)
            return

        item = Hostname(hostname), url, parse # InputItem(hostname, url, parse, False)
        yield item

        if self._ipv4regex.match(hostname) is not None or self._ipv6regex.match(hostname) is not None:
            return

        while True:
            _, hostname = hostname.split('.', maxsplit=1)
            if '.' not in hostname:
                return
            yield Hostname(hostname), url, parse

    async def _get_blocked(self, hostname: str) -> bool:
        from ..db_clients import get_sql_client
        from ..model.orm.allowlist import AllowlistHost
        return await AllowlistHost.exists(get_sql_client(), AllowlistHost.hostname == hostname, AllowlistHost.allowed == False)

    async def _is_blocked(self, hostname: str) -> bool:
        ret = self._hostname_blocked_cache.get(hostname, None)
        if ret is None:
            ret = self._hostname_blocked_cache[hostname] = await self._get_blocked(hostname)
        return ret

    async def is_blocked(self, url: str, parse: 'ParseResult') -> bool:
        for input_ in reversed(list(x[0] for x in self._gen_hostnames(url, parse))):
            if await self._is_blocked(input_[0]):
                return True
        return False

    async def process_rules(self, urls: AsyncIterable[tuple[T, str, 'ParseResult']], check_blocked=False) -> AsyncGenerator[T, None]:
        if self._stack is None:
            raise RuntimeError("Context manager must be entered first!")

        async for original, url, parse in urls:
            hostnames = list(self._gen_hostnames(url, parse))
            if check_blocked:
                blocked = False
                for input_ in reversed(hostnames):
                    if await self._is_blocked(input_[0]):
                        blocked = True
                        break
                if blocked:
                    continue

            for input_ in hostnames:
                if input_[0] not in self._hostname_rule_cache:
                    rules = self._hostname_rule_cache[input_[0]] = await self._get_hostname_rules(input_[0])
                else:
                    rules = self._hostname_rule_cache[input_[0]]

                if rules is None:
                    continue

                found = False
                for plugin_id, plugin_rules in rules.items():
                    if await self._rule_instances[plugin_id].matches(input_, plugin_rules):
                        yield original
                        found = True
                        break
                if found:
                    break

    @staticmethod
    async def _get_hostname_rules(hostname: Hostname) -> dict[str, set[str]]|None:
        from ..db_clients import get_sql_client
        from ..model.orm.allowlist import AllowlistHost, AllowlistRule
        client = get_sql_client()
        host = await AllowlistHost.find_one(client, AllowlistHost.hostname == hostname, AllowlistHost.allowed == True, attrs=(AllowlistHost.id,))
        if host is None:
            return None
        rules = {}
        async for rule in await AllowlistRule.find_all(client, AllowlistRule.host_id == host.id, attrs=(AllowlistRule.value, AllowlistRule.plugin_id)):
            if rule.plugin_id not in rules:
                rules[rule.plugin_id] = set()
            rules[rule.plugin_id].add(rule.value)
        return rules


