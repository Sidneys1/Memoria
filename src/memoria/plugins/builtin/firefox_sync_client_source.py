from logging import getLogger
from typing import TYPE_CHECKING, AsyncIterator

if TYPE_CHECKING:
    from pydantic import JsonValue

from memoria.plugins import Html
from memoria.plugins.source import HistoryImporter, ImportedHistory, PluginSchedule, Source, UxHost

_MOZILLA_URL = "https://www.mozilla.org/en-US/firefox/features/sync/"
_GITHUB_URL = "https://github.com/Mikescher/firefox-sync-client"
_DESC: Html = f"""<p>
    Collects web history
    <a href="{_MOZILLA_URL}" target="_blank" referrerpolicy="no-referrer">
        synced to a Mozilla account
    </a> using the open-source
    <a href="{_GITHUB_URL}" target="_blank" referrerpolicy="no-referrer">
        <code>ffsclient</code>
    </a>.
</p>"""

_LOGIN_FORM = """<div style="row-gap: 0.5em; grid-column: 1 / 3; display:grid; grid-template-columns: subgrid;" id="form-contents">
    <h2 style="grid-column: 1/3;margin-bottom:0;">Login</h2>
    <label for="username">Username</label>
    <input id="username" name="email" type="email" placeholder="Username" required>
    <label for="password">Password</label>
    <input id="password" name="password" type="password" placeholder="Password" required>
</div>"""

_TOTP_FORM = """<div style="row-gap: 0.5em; grid-column: 1 / 3; display:grid; grid-template-columns: subgrid;" id="form-contents">
    <h2 style="grid-column: 1/3;margin-bottom:0;">One-Time-Password</h2>
    <label for="totp">TOTP</label>
    <input type="text" id="totp" name="totp" maxlength="6" minlength="6" placeholder="TOTP" required>
</div>
"""

_LOG = getLogger(__spec__.name)

def _get_ffsclient_path() -> str|None:
    from shutil import which
    return which('ffsclient')

async def create_sync_client(host: UxHost) -> tuple[Html, 'JsonValue']:
    import asyncio
    import json
    from tempfile import TemporaryDirectory
    from pathlib import Path
    from asyncio.subprocess import create_subprocess_exec, DEVNULL, PIPE

    with TemporaryDirectory() as path:
        temp_path = Path(path) / 'session.json'

        result = await host.update_dialog(_LOGIN_FORM)
        assert isinstance(result, dict) and 'email' in result and isinstance(result['email'], str) and 'password' in result and isinstance(result['password'], str)

        email = result['email']

        await host.waiting("Logging in...")

        ffsclient_path = _get_ffsclient_path()
        assert ffsclient_path is not None

        CMD = (
            ffsclient_path,
            'login',
            email,
            result['password'],
            '--sessionfile', str(temp_path),
        )

        print('Running:', ' '.join(CMD))
        process = await create_subprocess_exec(*CMD, stdin=PIPE, stdout=DEVNULL, stderr=PIPE)

        assert process.stdout is not None and process.stdin is not None

        stderr = b''
        try:
            line = await asyncio.wait_for(process.stdout.readline(), 5)
            if line == b'Enter your OTP (2-Factor Authentication Code): \n':
                result = await host.update_dialog(_TOTP_FORM)
                assert isinstance(result, dict) and 'totp' in result and isinstance(result['totp'], str)
                await host.waiting()
                process.stdin.write(result['totp'].encode())

            _, stderr = await process.communicate()
            if stderr:
                _LOG.error("Expected success or TOTP request from subprocess, got %r.", line)
                raise ChildProcessError('Failed to log in.')
        except asyncio.TimeoutError:
            await host.error("Timed out waiting for login.")
            raise
        except ChildProcessError:
            first_line = stderr.find(b'\n') or 0
            last_line = stderr.rfind(b'\n', first_line, -1) or len(stderr)
            error = stderr[:first_line or len(stderr)].decode()
            import json
            details = error
            try:
                details = json.loads(stderr[last_line+1:-1].decode()).get('message')
            except ValueError:
                pass
            import html
            if not details:
                await host.error("""Failed to log in:<br><pre><code>{}</code></pre>""".format(html.escape(error)))
            else:
                await host.error("""Failed to log in: {}.""".format(html.escape(details)))
            raise


        with temp_path.open() as fp:
            session = json.load(fp)

        return f"Firefox Sync <samp>{email}</samp>", {'session': session}


class FirefoxSyncClientSource(Source):
    UX_CONFIG = Source.UxConfig(display_name="Firefox Sync", description=_DESC, create=create_sync_client)
    SUPPORTS_ON_DEMAND = True
    SUPPORTED_SCHEDULES = PluginSchedule.Intermittent | PluginSchedule.Scheduled | PluginSchedule.OnDemand

    _CHECK_SESSION_ARGS = ('check-session', )
    _HISTORY_LIST_ARGS = ('history', 'list', '--format', 'json', '--minimized-json', '--ignore-schema-errors')

    _firefox_sync_client_path: str | None

    def __init__(self, config: 'JsonValue') -> None:
        self._firefox_sync_client_path = _get_ffsclient_path()

    async def __aenter__(self):
        import asyncio
        from subprocess import DEVNULL

        if self._firefox_sync_client_path is None:
            raise EnvironmentError("`ffsclient` is not on PATH.")

        process = await asyncio.subprocess.create_subprocess_exec(self._firefox_sync_client_path,
                                                                  *self._CHECK_SESSION_ARGS,
                                                                  stdin=DEVNULL,
                                                                  stdout=DEVNULL,
                                                                  stderr=DEVNULL)
        if (await process.wait()) != 0:
            raise EnvironmentError("`ffsclient` does not have a valid session.")

        return await super().__aenter__()

    async def _stream_items(self) -> AsyncIterator[ImportedHistory]:
        from asyncio.subprocess import DEVNULL, PIPE, create_subprocess_exec

        import ijson

        from memoria.model.imported_history import ImportedMozillaHistory

        assert self._firefox_sync_client_path is not None

        process = await create_subprocess_exec(self._firefox_sync_client_path,
                                               *self._HISTORY_LIST_ARGS,
                                               stdin=DEVNULL,
                                               stdout=PIPE,
                                               stderr=DEVNULL)
        async for i in ijson.items(process.stdout, 'item'):
            i['last_visit'] = max(x['date_unix'] for x in i.get('visits'))
            yield ImportedMozillaHistory.model_validate(i)

    async def run(self, importer: HistoryImporter) -> None:
        await importer.add_many(self._stream_items())
