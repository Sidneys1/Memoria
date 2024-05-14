from datetime import UTC, datetime
from pathlib import Path
from typing import Any, AsyncGenerator, Iterable, Self

from pydantic import Field, field_validator

from .imported_history import ImportedHistory


class MozPlace(ImportedHistory):
    description: str | None
    visits: int

    @field_validator('last_visit', mode='before')
    def microseconds(cls, value: int|None) -> float | int:
        if value is None:
            return 0.0
        if value > 1_000_000_000_000:
            return value / 1000
        return value

    @classmethod
    def from_row(cls, row: Iterable[Any]):
        return cls(**{k: v for k, v in zip(cls.model_fields, row)})

    @classmethod
    async def from_sqlite_file(cls, path: Path, after: datetime | None = None) -> AsyncGenerator[Self, None]:
        import aiosqlite

        try:
            async with aiosqlite.connect(path) as con:
                async with con.execute("SELECT name FROM sqlite_master WHERE type='table';") as cursor:
                    tables = [x[0] async for x in cursor]
                    if len({'moz_places', 'moz_historyvisits'}.intersection(tables)) != 2:
                        raise ValueError(
                            f"The given file is not a Mozilla SQLite Database (missing table(s) `moz_places` and/or `moz_historyvisits` in: [`{'`, `'.join(tables)}`])."
                        )

                query = (
                    'SELECT moz_places.url, moz_places.title, MAX(moz_historyvisits.visit_date), moz_places.description, COUNT(moz_historyvisits.id) FROM moz_places'
                    ' JOIN moz_historyvisits ON moz_historyvisits.place_id = moz_places.id')
                if after is not None:
                    query += f' WHERE moz_historyvisits.visit_date > {int(after.astimezone(UTC).timestamp() * 1_000_000)}'
                query += ' GROUP BY moz_places.id'

                async with con.execute(f"{query};") as cursor:
                    async for row in cursor:
                        yield cls.from_row(row)
        except aiosqlite.DatabaseError as ex:
            raise ValueError("The given file is not a SQLite database.") from ex


CHROME_EPOC = int(datetime(1601, 1, 1, tzinfo=UTC).timestamp())


class ChromiumPlace(ImportedHistory):
    visit_count: int

    @field_validator('last_visit', mode='before')
    def nanoseconds(cls, value: int) -> float | int:
        if value > 10_000_000_000_000_000:
            return value / 1_000_000 + CHROME_EPOC
        return value

    @classmethod
    def from_row(cls, row: Iterable[Any]):
        return cls(**{k: v for k, v in zip(cls.model_fields, row)})

    @classmethod
    async def from_sqlite_file(cls, path: Path, after: datetime | None = None) -> AsyncGenerator[Self, None]:
        import aiosqlite

        try:
            async with aiosqlite.connect(path) as con:
                async with con.execute("SELECT name FROM sqlite_master WHERE type='table';") as cursor:
                    tables = [x[0] async for x in cursor]
                    if len({'urls', 'visits'}.intersection(tables)) != 2:
                        raise ValueError(
                            f"The given file is not a Chromium SQLite Database (missing table(s) `urls` and/or `visits` in: [`{'`, `'.join(tables)}`])."
                        )

                query = 'SELECT url, title, last_visit_time, visit_count FROM urls'
                if after is not None:
                    query += f' WHERE last_visit_time > {int((after.astimezone(UTC).timestamp() - CHROME_EPOC) * 1_000_000)}'

                async with con.execute(f"{query};") as cursor:
                    async for row in cursor:
                        yield cls.from_row(row)
        except aiosqlite.DatabaseError as ex:
            raise ValueError("The given file is not a SQLite database.") from ex
