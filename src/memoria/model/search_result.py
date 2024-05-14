from pydantic import Field

from .page import Page


class Result(Page):
    score: float
    basename: str | None = None
    explanation: dict[str, float] = Field(default_factory=dict)
