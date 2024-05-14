from abc import ABC
from datetime import datetime, UTC

from pydantic import BaseModel, computed_field, Field


class ImportedHistory(BaseModel, ABC):
    # id: str
    # """Some unique identifier."""

    url: str
    """History location."""

    title: str | None = None
    """History entry title."""

    last_visit: datetime
    """The last time this entry was visited."""


class ImportedMozillaHistory(ImportedHistory):

    class Visit(BaseModel):
        date: str
        date_unix: datetime
        transition: str
        transition_const: int

    url: str = Field(alias='uri')
    deleted: bool
    visits: list[Visit]

    # @computed_field
    # @property
    # def last_visit(self) -> datetime:
    #     if not self.visits:
    #         return datetime.fromtimestamp(0, UTC)
    #     return max(v.date_unix for v in self.visits)
