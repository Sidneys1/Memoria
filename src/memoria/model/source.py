from functools import lru_cache

from pydantic import BaseModel, computed_field

from ..plugins.source import PluginSchedule, Source as SourcePlugin


class Source(BaseModel):
    id: int
    plugin_id: str
    display_name: str
    config: str
    schedule: PluginSchedule
    schedule_value: str|None
    enabled: bool

    @computed_field
    def can_run_on_demand(self) -> bool:
        return PluginSchedule.OnDemand in self._get_plugin(self.plugin_id).SUPPORTED_SCHEDULES

    @computed_field
    def display_schedule(self) -> str:
        match self.schedule:
            case PluginSchedule.Disabled:
                return "Only on demand" if self.can_run_on_demand else "Disabled"
            case PluginSchedule.Continuous:
                return "Always running"
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
                assert isinstance(self.schedule_value, str)
                value = self.schedule_value
                try:
                    from cron_descriptor import get_description
                    return get_description(value)
                except Exception:
                    from logging import getLogger
                    getLogger(__spec__.name).exception('Failed to translate cron value %r.', value)
                    return f"Cron: {value}"
            case PluginSchedule.OnDemand:
                return "On Demand"

    # @computed_field
    # def display_name(self) -> str:
    #     config = self._get_options(self.plugin_id)
    #     ret = config.display_name or self.plugin_id
    #     print('!!!!!!! DIsplay name of', self.plugin_id, 'is', ret)
    #     return ret

    @staticmethod
    @lru_cache
    def _get_options(plugin_id: str) -> SourcePlugin.UxConfig:
        return Source._get_plugin(plugin_id).UX_CONFIG

    @staticmethod
    @lru_cache
    def _get_plugin(plugin_id: str) -> type[SourcePlugin]:
        from ..plugins._plugin_suite import PluginSuite, PluginId
        plugin = PluginSuite().get_plugin_by_id(PluginId(plugin_id))
        assert plugin is not None and issubclass(plugin.type, SourcePlugin), f"{plugin_id}"
        return plugin.type

    class Config:
        from_attributes = True
