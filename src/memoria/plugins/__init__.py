from abc import ABC
from contextlib import AbstractAsyncContextManager
from enum import IntFlag, auto
from typing import NewType

type Html = str
PluginId = NewType('PluginId', str)


class PluginSchedule(IntFlag):
    Disabled = 0
    """The plugin will not be run."""

    Continuous = auto()
    """The plugin will manage its own lifecycle (running continuously) through `__aenter__` and `__aexit__`."""

    Intermittent = auto()
    """The plugin can be configured to run at specific intervals."""

    Scheduled = auto()
    """The plugin can be configured to run at specific cron schedules."""

    OnDemand = auto()
    """The plugin can be run on-demand, even if other schedules are selected."""


class Plugin(AbstractAsyncContextManager, ABC):
    async def __aexit__(self, *_, **__):
        """Overridden here so as to satisfy the abstractmethod."""
        return None
