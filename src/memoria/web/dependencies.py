__dependencies__ = (
    "aiofiles~=23.2.1",
    "aiohttp~=3.9.5",
    "aiosqlite~=0.20.0",
    "beautifulsoup4~=4.12.3",
    "elasticsearch[async]~=8.13.1",
    "fasthx~=0.2403.1",
    "fastapi~=0.111.0",
    "ijson~=3.2.3",
    "humanize~=4.9.0",
    "pydantic-settings~=2.2.1",
    "python-magic~=0.4.27",
    "SQLAlchemy[asyncio]~=2.0.30",
)


def missing_dependencies() -> None:
    from pathlib import Path
    from shlex import quote
    from shutil import which
    from sys import executable, stderr

    if stderr.isatty():
        from ..util import BOLD_RED, CYAN, MONOKAI_STRING, RED
    else:
        RED = BOLD_RED = CYAN = MONOKAI_STRING = lambda x: x

    actual_exe = Path(executable).resolve()
    cmds = ('python', 'python3')
    cmd = None
    for c in cmds:
        if Path(which(c)).resolve() == actual_exe:
            cmd = c
            break
    if cmd is None:
        cmd = str(actual_exe)

    cmd += ' -m pip install '

    print(BOLD_RED("Failed to start Memoria: FastAPI not installed.\n\n") +
          RED("Did you install the dependencies?\n\n") + "Try running this:\n\n" + CYAN(cmd) +
          (' \\\n' + ' ' * len(cmd)).join(MONOKAI_STRING(quote(x)) for x in __dependencies__),
          sep='',
          file=stderr)
    exit(1)
