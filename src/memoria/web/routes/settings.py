from .. import APP
from . import HX


@APP.get('/settings/')
@HX.page('settings.html.j2')
async def settings() -> None:
    ...


__all__ = tuple()
