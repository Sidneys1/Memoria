from pathlib import Path
from sys import stderr, argv
from shutil import which
from subprocess import call

if __name__ == '__main__':
    if not (fastapi := which('fastapi')):
        print("FastAPI CLI not found. Install with `python3 -m pip install fastapi-cli`.", file=stderr)
        exit(1)

    try:
        exit(call([fastapi, 'run', *argv[1:], str(Path(__file__).parent)]))
    except KeyboardInterrupt:
        exit()
