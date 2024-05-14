from os import environ
from pathlib import Path


SECRETS_DIR = Path(environ.get('SECRETS_DIR', '/run/secrets'))
