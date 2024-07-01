from functools import lru_cache

from pydantic import BaseModel, Field, computed_field

from ..plugins.allowlist import AllowlistRule as AllowlistPlugin


class AllowlistRule(BaseModel):
    id: int
    host_id: int = Field(exclude=True)
    plugin_id: str = Field(exclude=True)
    value: str

    @computed_field
    def prefix(self) -> str|None:
        return self._get_options(self.plugin_id).prefix

    @computed_field
    def color(self) -> str|None:
        return self._get_options(self.plugin_id).color

    @staticmethod
    @lru_cache
    def _get_options(plugin_id: str) -> AllowlistPlugin.DisplayOptions|None:
        from ..plugins._plugin_suite import PluginSuite
        from ..plugins.allowlist import AllowlistRule
        suite = PluginSuite()
        for plugin in suite._plugins.values():
            if not issubclass(plugin, AllowlistRule): continue
            if plugin.identifier != plugin_id: continue
            if (options := plugin.DISPLAY_OPTIONS) is None:
                return None
            return options

    class Config:
        from_attributes = True


class AllowlistHost(BaseModel):
    id: int
    hostname: str

    rules: list[AllowlistRule]

class DenylistHost(BaseModel):
    id: int
    hostname: str
