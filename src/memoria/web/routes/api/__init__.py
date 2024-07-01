from enum import Enum
from typing import Annotated, TypeAlias

from fastapi import APIRouter, Header

from ... import APP


class HtmxHeaderValue(str, Enum):
    TRUE = 'true'

HtmxHeader: TypeAlias = Annotated[HtmxHeaderValue, Header()]
ContentType: TypeAlias = Annotated[str, Header()]

# Create router
API = APIRouter(prefix='/api/v1')


# Import routes
from .history import *
from .search import *
from .upload_db import *
from .allowlist import *
from .allowlist_rules import *
from .denylist import *

# Include router
APP.include_router(API)

__all__ = tuple()
