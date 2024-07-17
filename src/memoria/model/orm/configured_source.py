from sqlalchemy import Boolean, Integer, String

from . import Column, CrudBase


class ConfiguredSource(CrudBase):
    __tablename__ = 'configured_sources'

    id = Column(Integer, primary_key=True)
    plugin_id = Column(String)
    display_name = Column(String)
    config = Column(String, default="null")
    schedule = Column(Integer, default=0)
    schedule_value = Column(String, default="")
    enabled = Column(Boolean, default=False)


__all__ = tuple()
