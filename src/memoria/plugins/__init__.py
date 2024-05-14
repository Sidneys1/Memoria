from logging import getLogger
from itertools import chain, pairwise
from importlib.metadata import entry_points
from contextlib import AbstractAsyncContextManager
from typing import TYPE_CHECKING, Any, Coroutine, Iterable, Callable, Self

from .base import Plugin, Result
from .downloader import Downloader
from .extractor import Extractor
from .filter import Filter
from ..settings import SETTINGS
from ..model.imported_history import ImportedHistory

_LOG = getLogger(__spec__.name)


class PluginProcessor(AbstractAsyncContextManager):
    downloader: Downloader

    wants: list[set[str]]

    extractor: Extractor
    filters: list[Filter]
    _LOG = getLogger(__spec__.name + '.PluginProcessor')

    def __init__(self, downloader: type[Downloader], extractor: type[Extractor],
                 filters: Iterable[type[Filter]]) -> None:
        self.downloader = downloader()
        self.extractor = extractor()
        self.filters = [f() for f in filters]

        self.wants = []
        for left, right in pairwise(chain((self.downloader,), self.filters, (self.extractor,))):
            assert not isinstance(left, Extractor)
            assert not isinstance(right, Downloader)
            self.wants.append(left.content_types.intersection(right.accept))

    async def __aenter__(self) -> Self:
        await self.downloader.__aenter__()
        for filter_ in self.filters:
            await filter_.__aenter__()
        await self.extractor.__aenter__()
        return self

    async def __aexit__(self, *args, **kwargs) -> bool | None:
        await self.extractor.__aexit__(*args, **kwargs)
        for filter_ in self.filters:
            await filter_.__aexit__(*args, **kwargs)
        await self.downloader.__aexit__(*args, **kwargs)
        return None

    async def process_one(self, history: ImportedHistory, check_exists: Callable[[Result], Coroutine[None, None, bool]]) -> Result|None:
        result = await self.downloader.download(history.url, self.wants[0])
        if result is None:
            self._LOG.error("Could not download `%s`.", history.url)
            return None
        if await check_exists(result):
            self._LOG.info("URL `%s` has already been downloaded before, and the content is the same. Skipping.", history.url)
            return None

        self._LOG.debug("Item downloaded, meta=%r", result.meta)

        for filter_, wants in zip(self.filters, self.wants[1:]):
            result = await filter_.transform(result, wants)
            if result is None:
                self._LOG.error("Filter produced no output.")
                return None
            self._LOG.debug("Item filtered, meta=%r", result.meta)

        ret = await self.extractor.extract(result)
        self._LOG.debug("Item extracted, meta=%r", result.meta)
        return ret


class PluginSuite:
    _modules: dict[str, str]
    _plugins: dict[str, type[Plugin]]

    _downloaders: dict[str, type[Downloader]]
    _extractors: dict[str, type[Extractor]]
    _filters: dict[str, type[Filter]]

    def __init__(self) -> None:
        from .builtin.aiohttp_downloader import AiohttpDownloader
        from .builtin.html_content_finder import HtmlContentFinder
        from .builtin.html_extractor import HtmlExtractor

        self._modules = {
            'AiohttpDownloader': 'memoria.plugins.builtin.aiohttp_downloader',
            'HtmlContentFinder': 'memoria.plugins.builtin.html_content_finder',
            'HtmlExtractor': 'memoria.plugins.builtin.html_extractor'
        }
        self._plugins = {
            'AiohttpDownloader': AiohttpDownloader,
            'HtmlContentFinder': HtmlContentFinder,
            'HtmlExtractor': HtmlExtractor
        }

        self._downloaders = {'AiohttpDownloader': AiohttpDownloader}
        self._extractors = {'HtmlExtractor': HtmlExtractor}
        self._filters = {'HtmlContentFinder': HtmlContentFinder}

        for entry_point in entry_points(group='memoria'):
            if entry_point.module.startswith('memoria.plugins.builtin.'):
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

        if issubclass(plugin, Downloader):
            _LOG.debug("\tPlugin `%s` is a Downloader, producing [`%s`].", name, '`, `'.join(plugin.content_types))
            self._downloaders[name] = plugin

        if issubclass(plugin, Extractor):
            _LOG.debug("\tPlugin `%s` is an Extractor, consuming [`%s`].", name, '`, `'.join(plugin.accept))
            self._extractors[name] = plugin

        if issubclass(plugin, Filter):
            _LOG.debug("\tPlugin `%s` is a Filter, consuming [`%s`] and producing [`%s`].", name,
                       '`, `'.join(plugin.accept), '`, `'.join(plugin.content_types))
            self._filters[name] = plugin

    def _check(self) -> None:
        errors: list[Exception] = []

        if SETTINGS.downloader not in self._downloaders:
            errors.append(
                ValueError(f"No Downloader plugin by name `{SETTINGS.downloader}`. "
                           f"Available Downloaders: [`{'`, `'.join(self._downloaders)}`]"))

        if SETTINGS.extractor not in self._extractors:
            errors.append(
                ValueError(f"No Extractor plugin by name `{SETTINGS.extractor}`. "
                           f"Available Extractors: [`{'`, `'.join(self._extractors)}`]"))

        if errors:
            raise ExceptionGroup("Invalid configuration:", errors)

        downloader = self._downloaders[SETTINGS.downloader]
        extractor = self._extractors[SETTINGS.extractor]

        c_type = downloader.content_types
        for i, name in enumerate(SETTINGS.filter_stack, start=1):
            _LOG.debug("Checking filter #%d: %r", i, name)
            if name not in self._plugins:
                errors.append(ValueError(f"No plugin by name `{name}`."))
                continue
            if name not in self._filters:
                errors.append(
                    ValueError(f"No Fiter plugin by name `{name}`. "
                               f"Available Filters: [`{'`, `'.join(self._filters)}`]"))
                continue
            if not c_type.intersection(self._filters[name].accept):
                errors.append(
                    ValueError(f"Filter #{i} (`{name}`) of accepts only "
                               f"[`{'`, `'.join(self._filters[name].accept)}`], but the previous "
                               f"plugin only produces [`{'`, `'.join(c_type)}`]."))
                continue

            _LOG.debug("\tFilter #%d: `%s` [`%s`] -> [`%s`]", i, name,
                       '`, `'.join(c_type.intersection(self._filters[name].accept)),
                       '`, `'.join(self._filters[name].content_types))
            c_type = self._filters[name].content_types

        if not c_type.intersection(extractor.accept):
            errors.append(
                ValueError(f"Filter stack produces [`{'`, `'.join(c_type)}`], but selected Extractor "
                           f"`{SETTINGS.extractor}` only accepts [`{'`, `'.join(extractor.accept)}`]."))

        if errors:
            raise ExceptionGroup("Plugin stack is invalid:", errors)

    def create_processor(self) -> PluginProcessor:
        return PluginProcessor(self._downloaders[SETTINGS.downloader], self._extractors[SETTINGS.extractor],
                               (self._filters[name] for name in SETTINGS.filter_stack))
