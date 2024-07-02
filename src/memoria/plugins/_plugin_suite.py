from importlib.metadata import entry_points
from logging import getLogger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ._processing_manager import ProcessingPluginManager

from ..settings import SETTINGS
from ..util import Singleton
from .processing import Downloader, Extractor, Filter, Plugin

_LOG = getLogger(__spec__.name)


class PluginSuite(metaclass=Singleton):
    _modules: dict[str, str]
    _plugins: dict[str, type[Plugin]]

    def __init__(self) -> None:
        from .builtin.aiohttp_downloader import AiohttpDownloader
        from .builtin.html_content_finder import HtmlContentFinder
        from .builtin.html_extractor import HtmlExtractor
        from .builtin.prefix_allowlistrule import PrefixAllowlistRule
        from .builtin.regex_allowlistrule import RegexAllowlistRule

        self._modules = {
            'AiohttpDownloader': 'memoria.plugins.builtin.aiohttp_downloader',
            'HtmlContentFinder': 'memoria.plugins.builtin.html_content_finder',
            'HtmlExtractor': 'memoria.plugins.builtin.html_extractor',
            'PrefixAllowlistRule': 'memoria.plugins.buitin.prefix_allowlistrule',
            'RegexAllowlistRule': 'memoria.plugins.buitin.regex_allowlistrule',
        }
        self._plugins = {
            'AiohttpDownloader': AiohttpDownloader,
            'HtmlContentFinder': HtmlContentFinder,
            'HtmlExtractor': HtmlExtractor,
            'PrefixRule': PrefixAllowlistRule,
            'RegexRule': RegexAllowlistRule,
        }

        for entry_point in entry_points(group='memoria'):
            if entry_point.module.startswith('memoria.plugins.builtin.'):
                _LOG.debug("Skipping import of built-in plugin `%s.%s`", entry_point.module, entry_point.name)
                continue
            _LOG.debug("Importing plugin `%s` in `%s`.", entry_point.name, entry_point.module)

            try:
                plugin = entry_point.load()
                if not issubclass(plugin, Plugin):
                    _LOG.error("Plugin `%s` does not adhere to API!", entry_point.name)
                    continue
                self._add_plugin(entry_point.module, entry_point.name, plugin)
            except:
                _LOG.exception("Failed to load `%s`:", entry_point.value)
        _LOG.info("Loaded plugins: [`%s`]", '`, `'.join(self._plugins.keys()))
        self._check()

    def _add_plugin(self, module: str, name: str, plugin: type[Plugin]) -> None:
        if name in self._plugins:
            if (fqdn := f'{module}.{name}') in self._plugins:
                raise RuntimeError(f"Same module used twice despite disambiguation: {fqdn}!")

            _LOG.warning("Same plugin name used twice (in `%s` first, and now `%s`). Renaming current plugin to `%s`.",
                         self._modules[name], module, fqdn)
            name = fqdn

        self._modules[name] = module
        self._plugins[name] = plugin

    def _check(self) -> None:
        errors: list[Exception] = []

        if SETTINGS.downloader not in self._plugins or not issubclass(self._plugins[SETTINGS.downloader], Downloader):
            errors.append(
                ValueError(f"No Downloader plugin by name `{SETTINGS.downloader}`. "
                           f"Available Downloaders: [`{'`, `'.join(self._downloaders)}`]"))

        if SETTINGS.extractor not in self._plugins or not issubclass(self._plugins[SETTINGS.extractor], Extractor):
            errors.append(
                ValueError(f"No Extractor plugin by name `{SETTINGS.extractor}`. "
                           f"Available Extractors: [`{'`, `'.join(self._extractors)}`]"))

        for filter_ in SETTINGS.filter_stack:
            if filter_ not in self._plugins or not issubclass(self._plugins[filter_], Filter):
                errors.append(
                    ValueError(
                        f"No Filter plugin by name `{filter_}`. "
                        f"Available Filters: [`{'`, `'.join(n for n, t in self._plugins.items() if issubclass(t, Filter))}`]"
                    ))

        if errors:
            raise ExceptionGroup("Invalid configuration:", errors)

    def create_processing_manager(self) -> 'ProcessingPluginManager':
        from ._processing_manager import ProcessingPluginManager
        return ProcessingPluginManager(self._plugins[SETTINGS.downloader], self._plugins[SETTINGS.extractor],
                                       (self._plugins[name] for name in SETTINGS.filter_stack))
