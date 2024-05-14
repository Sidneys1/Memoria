from datetime import datetime

from pydantic import BaseModel


class History(BaseModel):
    url: str
    """History location."""

    title: str | None = None
    """History entry title."""

    last_visit: datetime
    last_scrape: datetime|None = None

    class Config:
        from_attributes = True
