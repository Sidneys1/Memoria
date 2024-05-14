from sqlalchemy import DateTime, String, ForeignKey
from sqlalchemy.orm import relationship

from . import CrudBase, Column


class Page(CrudBase):
    __tablename__ = 'pages'

    id = Column(String, primary_key=True)
    url = Column(String, ForeignKey("history.url"))
    title = Column(String, nullable=True)
    timestamp = Column(DateTime)

    author = Column(String, nullable=True)
    favicon = Column(String, nullable=True)
    description = Column(String, nullable=True)

    owner = relationship("History", back_populates="pages")

__all__ = tuple()
