from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from . import Column, CrudBase


class AllowlistHost(CrudBase):
    __tablename__ = 'allowlist_hosts'

    id = Column(Integer, primary_key=True)
    hostname = Column(String, unique=True)
    allowed = Column(Boolean)

    rules = relationship("AllowlistRule", back_populates="host")


class AllowlistRule(CrudBase):
    __tablename__ = 'allowlist_rules'

    id = Column(Integer, primary_key=True)
    host_id = Column(Integer, ForeignKey("allowlist_hosts.id"))
    plugin_id = Column(String)
    value = Column(String)

    host = relationship("AllowlistHost", back_populates="rules")


__all__ = tuple()
