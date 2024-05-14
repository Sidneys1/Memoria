from sqlalchemy import DateTime, String
from sqlalchemy.orm import relationship

from . import CrudBase, Column

class History(CrudBase):
    __tablename__ = 'history'

    url = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    last_visit = Column(DateTime)
    last_scrape = Column(DateTime, nullable=True)

    pages = relationship("Page", back_populates="owner")

__all__ = tuple()
