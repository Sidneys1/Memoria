from datetime import datetime

from pydantic import BaseModel, Field


class Page(BaseModel):
    id: str = Field(alias='_id')
    url: str
    title: str
    timestamp: datetime

    # Optional (only if found on page)
    author: str | None = None
    favicon: str | None = None
    description: str | None = None

    class Config:
        from_attributes = True
