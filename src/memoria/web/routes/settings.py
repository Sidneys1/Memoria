from .. import APP
from . import HX


@APP.get('/settings/')
@HX.page('settings.html.j2')
async def settings():
    from ...plugins._plugin_suite import PluginSuite
    from ...plugins.allowlist import AllowlistRule
    suite = PluginSuite()
    return {'rule_plugin_docs': [(x.identifier, x.LONG_DOCUMENTATION, x.LONG_DOC_EXAMPLES) for x in suite._plugins.values() if issubclass(x, AllowlistRule) and x.LONG_DOCUMENTATION is not None]}


__all__ = tuple()
