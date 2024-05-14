from fastapi.staticfiles import StaticFiles
from fasthx import Jinja

from .. import APP, TEMPLATES, WWW_ROOT

HX = Jinja(TEMPLATES)

from .about import *

# API Routes
from .api import *
from .history import *

# Web Routes
from .index import *
from .settings import *

# Static
APP.mount('/static', StaticFiles(directory=WWW_ROOT / 'static'), name='static')

__all__ = tuple()
