from dataclasses import dataclass
from importlib.metadata import entry_points
from logging import getLogger
from typing import Generator, TypeVar, cast

from ..settings import SETTINGS
from ..util import Singleton
from . import PluginId
from .processing import Downloader, Extractor, Filter, Plugin

_LOG = getLogger(__spec__.name)

TPlugin = TypeVar('TPlugin', bound=Plugin)

@dataclass(repr=False, eq=False, frozen=True, slots=True)
class PluginDefinition[TPlugin]:
    id: PluginId
    short_name: str
    type: type[TPlugin]

class PluginSuite(metaclass=Singleton):
    _plugins: dict[PluginId, PluginDefinition[Plugin]]
    _short_names: dict[str, PluginId]

    def __init__(self) -> None:
        from .builtin.aiohttp_downloader import AiohttpDownloader
        from .builtin.firefox_sync_client_source import FirefoxSyncClientSource
        from .builtin.html_content_finder import HtmlContentFinder
        from .builtin.html_extractor import HtmlExtractor
        from .builtin.prefix_allowlistrule import PrefixAllowlistRule
        from .builtin.regex_allowlistrule import RegexAllowlistRule

        self._plugins = {}
        self._short_names = {}

        builtin_plugins = {
            PluginId('memoria.plugins.builtin.aiohttp_downloader:AiohttpDownloader'): AiohttpDownloader,
            PluginId('memoria.plugins.builtin.html_content_finder:HtmlContentFinder'): HtmlContentFinder,
            PluginId('memoria.plugins.builtin.html_extractor:HtmlExtractor'): HtmlExtractor,
            PluginId('memoria.plugins.builtin.prefix_allowlistrule:PrefixAllowlistRule'): PrefixAllowlistRule,
            PluginId('memoria.plugins.builtin.regex_allowlistrule:RegexAllowlistRule'): RegexAllowlistRule,
            PluginId('memoria.plugins.builtin.firefox_sync_client_source:FirefoxSyncClientSource'): FirefoxSyncClientSource,
        }

        for id, type in builtin_plugins.items():
            module, name = id.rsplit(':', maxsplit=1)
            self._add_plugin(id, module, name, type)

        for entry_point in entry_points(group='memoria'):
            if entry_point.module.startswith('memoria.plugins.builtin.'):
                continue

            _LOG.debug("Importing plugin `%s` in `%s`.", entry_point.name, entry_point.module)

            try:
                plugin = entry_point.load()
                if not issubclass(plugin, Plugin):
                    _LOG.error("Plugin `%s` does not adhere to API!", entry_point.name)
                    continue
                self._add_plugin(PluginId(entry_point.value), entry_point.module, entry_point.name, plugin)
            except:
                _LOG.exception("Failed to load `%s`:", entry_point.value)

        _LOG.info("Loaded plugins: [`%s`]", '`, `'.join(self._short_names.keys()))
        self._check()

    def _add_plugin(self, id: PluginId, module: str, name: str, plugin: type[Plugin]) -> None:
        if id in self._plugins:
            _LOG.warning("Same plugin (`%s`) imported twice?", id)
            return

        if name in self._short_names:
            _LOG.warning("Plugin name `%s` reused (first as `%s`, now `%s`).", name, self._short_names[name], id)
            name = id
            if name in self._short_names:
                _LOG.error("Plugin name still collides after disambiguation! Skipping.")
                return

        self._short_names[name] = id
        self._plugins[id] = PluginDefinition(id, name, plugin)

    def _check(self) -> None:
        errors: list[Exception] = []

        if SETTINGS.downloader not in self._short_names or not issubclass(self._plugins[self._short_names[SETTINGS.downloader]].type, Downloader):
            errors.append(
                ValueError(f"No Downloader plugin by name `{SETTINGS.downloader}`. "
                           f"Available Downloaders: [`{'`, `'.join(x.short_name for x in self.get_plugins_of_type(Downloader))}`]"))

        if SETTINGS.extractor not in self._short_names or not issubclass(self._plugins[self._short_names[SETTINGS.extractor]].type, Extractor):
            errors.append(
                ValueError(f"No Extractor plugin by name `{SETTINGS.extractor}`. "
                           f"Available Extractors: [`{'`, `'.join(x.short_name for x in self.get_plugins_of_type(Extractor))}`]"))

        for filter_ in SETTINGS.filter_stack:
            if filter_ not in self._short_names or not issubclass(self._plugins[self._short_names[filter_]].type, Filter):
                errors.append(
                    ValueError(
                        f"No Filter plugin by name `{filter_}`. "
                        f"Available Filters: [`{'`, `'.join(x.short_name for x in self.get_plugins_of_type(Filter))}`]"
                    ))

        if errors:
            raise ExceptionGroup("Invalid configuration:", errors)

    def get_plugins_of_type(self, t: type[TPlugin]) -> Generator[PluginDefinition[TPlugin], None, None]:
        for plugin in self._plugins.values():
            if issubclass(plugin.type, t):
                yield cast(PluginDefinition[t], plugin)

    def get_plugin_by_id(self, id: PluginId) -> PluginDefinition[Plugin] | None:
        return self._plugins[id]

    def get_plugin_by_short_name(self, short_name: str) -> PluginDefinition[Plugin] | None:
        if short_name not in self._short_names:
            return None
        return self._plugins[self._short_names[short_name]]
