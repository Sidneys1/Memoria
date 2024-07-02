from contextlib import AbstractAsyncContextManager
from itertools import chain, pairwise
from logging import getLogger
from typing import Callable, Coroutine, Iterable, Self

from ..model.imported_history import ImportedHistory
from ..settings import SETTINGS
from .processing import Downloader, Extractor, Filter, Plugin, Result


def _get_plugin_subclass(clazz: type) -> str:
    assert issubclass(clazz, Plugin), f"`{clazz.__name__}` is not a Plugin at all."
    assert clazz is not Plugin

    last: None | type[Plugin] = None
    for super_clazz in clazz.mro():
        if super_clazz is Plugin:
            break
        last = super_clazz

    assert last is not None
    return last.__name__


class ProcessingPluginManager(AbstractAsyncContextManager):
    downloader: Downloader

    wants: list[set[str]]

    extractor: Extractor
    filters: list[Filter]
    _LOG = getLogger(__spec__.name + '.PluginProcessor')

    def __init__(self, downloader: type[Downloader], extractor: type[Extractor],
                 filters: Iterable[type[Filter]]) -> None:
        errors = []

        if not issubclass(downloader, Downloader):
            errors.append(
                "Configured Downloader plugin is not valid: it's a "
                f"`{_get_plugin_subclass(downloader)}` instead of a `Downloader`.", )
        if not issubclass(extractor, Extractor):
            errors.append(
                "Configured Extractor plugin is not valid: it's a "
                f"`{_get_plugin_subclass(extractor)}` instead of an `Extractor`.", )

        c_type: None | set[str] = self.downloader.content_types
        for i, filter_ in enumerate(filters, start=1):
            if not issubclass(filter_, Filter):
                errors.append(
                    "Configured Filter plugin is not valid: it's a "
                    f"`{_get_plugin_subclass(filter_)}` instead of an `Filter`.", )
                c_type = None
                break

            if not c_type.intersection(filter_.accept):
                errors.append(
                    ValueError(f"Filter #{i} (`{filter_.__name__}`) of accepts only "
                               f"[`{'`, `'.join(filter_.accept)}`], but the previous "
                               f"plugin only produces [`{'`, `'.join(c_type)}`]."))
                continue

            _LOG.debug("\tFilter #%d: `%s` [`%s`] -> [`%s`]", i, filter_.__name__,
                       '`, `'.join(c_type.intersection(filter_.accept)), '`, `'.join(filter_.content_types))
            c_type = filter_.content_types

        if c_type is None:
            errors.append(f"Filter stack broken - cannot check Extractor accepted Content-Types.")
        else:
            if not c_type.intersection(extractor.accept):
                errors.append(
                    ValueError(f"Extractor stack accepts only "
                               f"[`{'`, `'.join(extractor.accept)}`], but the filter stack "
                               f"only produces [`{'`, `'.join(c_type)}`]."))

        if errors:
            raise ExceptionGroup("Invalid Processing plugin configuration.", errors)

        self.downloader = downloader()
        self.extractor = extractor()
        self.filters = [f() for f in filters]

        if not c_type.intersection(self.extractor.accept):
            errors.append(
                ValueError(f"Filter stack produces [`{'`, `'.join(c_type)}`], but selected Extractor "
                           f"`{SETTINGS.extractor}` only accepts [`{'`, `'.join(extractor.accept)}`]."))

        self.wants = []
        for left, right in pairwise(chain((self.downloader, ), self.filters, (self.extractor, ))):
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

    async def process_one(self, history: ImportedHistory,
                          check_exists: Callable[[Result], Coroutine[None, None, bool]]) -> Result | None:
        result = await self.downloader.download(history.url, self.wants[0])
        if result is None:
            self._LOG.error("Could not download `%s`.", history.url)
            return None
        if await check_exists(result):
            self._LOG.info("URL `%s` has already been downloaded before, and the content is the same. Skipping.",
                           history.url)
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
