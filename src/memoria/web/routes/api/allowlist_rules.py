from fastapi import Form

from ....model.allowlist import AllowlistRule
from ...db_dependencies import SqlSession
from .. import HX
from . import API


@API.delete("/allowlist-rules/{id}")
@HX.hx('blank.html.j2')
async def api_delete_allowlist_rule(session: SqlSession, id: int):
    from ....model.orm.allowlist import AllowlistRule as OrmRule
    async with session.begin():
        await session.delete(await OrmRule.find_one(session, OrmRule.id == id))


@API.put("/allowlist-rules/{id}", response_model=AllowlistRule)
@HX.hx('allowlist_rule.html.j2')
async def api_put_allowlist_rule(session: SqlSession, id: int, value: str = Form()):
    from ....model.orm.allowlist import AllowlistRule as OrmRule
    async with session.begin():
        rule = await OrmRule.find_one(session, OrmRule.id == id)
        rule.value = value
        await session.commit()
        return AllowlistRule(id=rule.id, host_id=rule.host_id, plugin_id=rule.plugin_id, value=rule.value).model_dump()


@API.post("/allowlist/{hostname}/rules", response_model=AllowlistRule)
@HX.hx('allowlist_rule.html.j2')
async def api_post_allowlist_rule(session: SqlSession, hostname: str, plugin_id: str = Form(), value: str = Form()):
    from ....model.orm.allowlist import AllowlistRule as OrmRule, AllowlistHost as OrmHost
    async with session.begin():
        host = await OrmHost.find_one(session, OrmHost.hostname == hostname, OrmHost.allowed == True)
        rule = OrmRule(host_id=host.id, plugin_id=plugin_id, value=value)
        session.add(rule)
        await session.commit()
        return AllowlistRule.model_validate(rule).model_dump()


__all__ = tuple()
