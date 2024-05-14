from .. import APP
from . import HX


@APP.get('/history/')
@HX.page('history.html.j2')
async def history() -> None:
    ...


__all__ = tuple()
