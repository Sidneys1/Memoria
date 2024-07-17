from typing import Annotated, AsyncGenerator, TYPE_CHECKING, cast
from urllib.parse import quote_plus
from logging import getLogger
import json

from fastapi import Form, Response, WebSocket, HTTPException, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ....plugins.source import Source, Html, UxHost, PluginSchedule
from ....plugins._plugin_suite import PluginSuite
from ....model.plugins import SourcePlugin
from ....model.orm.configured_source import ConfiguredSource
from ...db_dependencies import SqlSession
from ... import APP
from .. import HX
from . import API, HtmxHeader

if TYPE_CHECKING:
    from pydantic import JsonValue

_LOG = getLogger(__spec__.name)

@API.get("/plugins/sources")
@HX.hx('source_plugins.html.j2')
async def source_plugins() -> list[SourcePlugin]:
    ret: list[SourcePlugin] = []
    for plugin in PluginSuite().get_plugins_of_type(Source):
        if (display_name := plugin.type.UX_CONFIG.display_name) is None:
            display_name = plugin.short_name
        if (description := plugin.type.UX_CONFIG.description) is None:
            description = plugin.type.__doc__

        ret.append(SourcePlugin(id=plugin.id, display_name=display_name, description=description))

    return ret

@API.get("/plugins/sources/create")
@HX.hx('blank.html.j2', no_data=True)
async def source_create() -> None:
    return None

class Ux(UxHost):
    _is_reset: bool
    def __init__(self, ws: WebSocket):
        self._is_reset = False
        self._ws = ws

    async def error(self, message: Html) -> None:
        if self._is_reset:
            raise RuntimeError('Websocket has been closed.')
        await self._ws.close(code=1011, reason=message)
        self._is_reset = True

    async def done(self) -> None:
        if self._is_reset:
            raise RuntimeError('Websocket has been closed.')
        await self._ws.close()
        self._is_reset = True

    async def waiting(self, text: Html|None = None) -> None:
        if self._is_reset:
            raise RuntimeError('Websocket has been closed.')
        await self._ws.send_text(f"""
<div id="form-contents" style="grid-column:1 / 3;text-align:center;">
<div>{text}</div>
<img src="{APP.url_path_for('static', path='/oval.svg')}" width="38" alt="" />
</div>
""")

    async def update_dialog(self, form: Html) -> 'JsonValue':
        if self._is_reset:
            raise RuntimeError('Websocket has been closed.')
        await self._ws.send_text(form)
        ret = await self._ws.receive_json()
        if 'HEADERS' in ret:
            del ret['HEADERS']
        return cast('JsonValue', ret)

_RUN_ON = """<label for="form-source-schedule">Run on</label><select id="form-source-schedule" name="schedule_type">{options}</select>"""

_SCHEDULE_FORM = """<div id="form-contents" style="display: grid; grid-column: 1/3; grid-template-columns: subgrid; gap: 0.5em 1em;">
    <label for="form-source-enabled">Enabled</label>
    <input id="form-source-enabled" name="enabled" type="checkbox" style="justify-self: left;">

    {run_on}

    <label for="form-source-timer">Timer</label>
    <div>Every <input id="form-source-timer" name="timer" type="number" value="60" min="15" max="1440"> minutes.</div>

    <h2 style="grid-column: 1/3;">Schedule</h2>
    <div style="grid-column: 1/3;">At <select>
        <option>Midnight</option>
        <option>1 AM</option>
        <option>2 AM</option>
        <option>3 AM</option>
        <option>4 AM</option>
        <option>5 AM</option>
        <option>6 AM</option>
        <option>7 AM</option>
        <option>8 AM</option>
        <option>9 AM</option>
        <option>10 AM</option>
        <option>11 AM</option>
        <option selected>Noon</option>
        <option>1 PM</option>
        <option>2 PM</option>
        <option>3 PM</option>
        <option>4 PM</option>
        <option>5 PM</option>
        <option>6 PM</option>
        <option>7 PM</option>
        <option>8 PM</option>
        <option>9 PM</option>
        <option>10 PM</option>
        <option>11 PM</option>
    </select> <select>
        <option>every day</option>
        <option>on weekdays</option>
        <option>on weekends</option>
        <option>on Sundays</option>
        <option>on Mondays</option>
        <option>on Tuesdays</option>
        <option>on Wednesdays</option>
        <option>on Thursdays</option>
        <option>on Fridays</option>
        <option>on Saturdays</option>
    </select>.</div>
</div>"""

@API.websocket("/plugins/sources/create")
async def source_create_websocket(ws: WebSocket, session: SqlSession):
    try:
        await ws.accept()
        msg = await ws.receive_json()
        if 'id' not in msg or not isinstance(msg['id'], str):
            _LOG.error("id not provided")
            await ws.close()
            return

        plugin = PluginSuite().get_plugin_by_id(msg['id'])
        if plugin is None or not issubclass(plugin.type, Source):
            _LOG.error("Requested Source plugin `%s` does not exist.", msg['id'])
            await ws.close()
            return

        ux = Ux(ws)
        options = ""
        for value in plugin.type.SUPPORTED_SCHEDULES:
            match value:
                case PluginSchedule.OnDemand | PluginSchedule.Continuous:
                    continue
                case PluginSchedule.Intermittent:
                    options += f'<option value="{value.value}">a Timer</option>'
                case PluginSchedule.Scheduled:
                    options += f'<option value="{value.value}">a Schedule</option>'
        form  = _SCHEDULE_FORM
        run_on = ""
        if options:
            run_on = _RUN_ON.format(options=options)

        form = form.format(run_on=run_on)

        values = await ux.update_dialog(form)
        print(values)
        await ux.done()
        return

        if plugin.type.UX_CONFIG.create is None:
            # No workflow.
            # await ws.send_text(f"""<div id="new-source-form">done</div>""")
            await ux.done()
            return


        try:
            display_name, config = await plugin.type.UX_CONFIG.create(ux)
        except Exception as ex:
            await ux.error(str(ex))
            return

        if not ux._is_reset:
            await ux.done()

        source = ConfiguredSource(plugin_id=msg['id'], display_name=display_name, config=json.dumps(config))
        session.add(source)
    except WebSocketDisconnect:
        print('client disconnected')

# @API.get("/plugins/sources")
# async def source_plugins(id: str = Form()) -> Plugin:
#     plugin = PluginSuite().get_plugin_by_id(id)
#     if not issubclass(plugin, Source):
#         raise HTTPException(404)
#     plugin.UX_CONFIG.


__all__ = tuple()
