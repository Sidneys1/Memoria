import logging
import sys
from pathlib import Path
from datetime import datetime, timedelta

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.templating import Jinja2Templates
except ImportError:
    from .dependencies import missing_dependencies
    missing_dependencies()

from humanize import naturaltime

from .. import MODULE_LOGGER
from ..util import ColorFormatter
from .lifecycle import lifespan
# from .jinja import relative_time

ROOT = Path(__file__).parent.resolve()
WWW_ROOT = ROOT / 'www'

TEMPLATES = Jinja2Templates(WWW_ROOT / 'templates', extensions=['jinja2.ext.debug', 'jinja2.ext.loopcontrols'])
TEMPLATES.env.globals['now'] = datetime.now
TEMPLATES.env.filters['natural_time'] = naturaltime

APP = FastAPI(lifespan=lifespan)

APP.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=False, allow_methods=['*'], allow_headers=['*', 'HX-Push-Url'])

logger = MODULE_LOGGER
logger.level = logging.DEBUG
handler = logging.StreamHandler()
handler.setLevel(logger.level)
handler.setFormatter(ColorFormatter())
logger.addHandler(handler)

from .routes import *
