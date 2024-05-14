from ...__about__ import *
from .. import APP
from . import HX


@APP.get('/about/')
@HX.page('about.html.j2')
async def about() -> None:
    return {'version': __version__, 'description': __description__, 'authors': __authors__}


__all__ = tuple()
