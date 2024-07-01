from .. import APP
from . import HX

@APP.get('/settings/')
@HX.page('settings.html.j2')
async def settings():
    from ...plugins._plugin_suite import PluginSuite
    from ...plugins.allowlist import AllowlistRule
    suite = PluginSuite()
    plugins = {}
    docs = {}
    for plugin in (x for x in suite._plugins.values() if issubclass(x, AllowlistRule)):
        ident = plugin.identifier
        if plugin.DISPLAY_OPTIONS is not None:
            plugins[ident] = {'display_name': plugin.DISPLAY_OPTIONS.display_name or ident, 'color': plugin.DISPLAY_OPTIONS.color, 'prefix': plugin.DISPLAY_OPTIONS.prefix}
        else:
            plugins[ident] = {'display_name': ident, 'color': None, 'prefix': None}

        if plugin.LONG_DOCUMENTATION is not None:
            docs[ident] = plugin.LONG_DOCUMENTATION, plugin.SHORT_DOCUMENTATION, plugin.LONG_DOC_EXAMPLES


    return {'rule_plugin_docs': docs, 'plugins': plugins}


__all__ = tuple()
