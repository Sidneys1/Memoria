from pydantic import BaseModel, computed_field

from ..plugins.source import PluginSchedule


class Source(BaseModel):
    id: int
    plugin_id: str
    display_name: str
    config: str
    schedule: PluginSchedule
    schedule_value: str|None
    enabled: bool

    @computed_field
    def display_schedule(self) -> str:
        match self.schedule:
            case PluginSchedule.Disabled:
                return "disabled"
            case PluginSchedule.Continuous:
                return "Continuous"
            case PluginSchedule.Intermittent:
                assert isinstance(self.schedule_value, str)
                value = float(self.schedule_value)
                if value == 60:
                    return "Hourly"
                elif value == 1440:
                    return "Daily"
                import humanize
                return "Every " + humanize.naturaldelta(60.0 * value)
            case PluginSchedule.Scheduled:
                return "Scheduled"
            case PluginSchedule.OnDemand:
                return "OnDemand"

    # @computed_field
    # def display_name(self) -> str:
    #     config = self._get_options(self.plugin_id)
    #     ret = config.display_name or self.plugin_id
    #     print('!!!!!!! DIsplay name of', self.plugin_id, 'is', ret)
    #     return ret

    # @staticmethod
    # @lru_cache
    # def _get_options(plugin_id: str) -> SourcePlugin.UxConfig:
    #     from ..plugins._plugin_suite import PluginSuite, PluginId
    #     plugin = PluginSuite().get_plugin_by_id(PluginId(plugin_id))
    #     assert plugin is not None and issubclass(plugin.type, SourcePlugin), f"{plugin_id}"
    #     return plugin.type.UX_CONFIG

    class Config:
        from_attributes = True
