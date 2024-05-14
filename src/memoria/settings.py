from os import cpu_count
from pathlib import Path

from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from .env import SECRETS_DIR

CPU_COUNT = cpu_count()

class Settings(BaseSettings):
    model_config = SettingsConfigDict(secrets_dir=SECRETS_DIR, env_prefix='memoria_')

    elastic_password: str
    elastic_user: str = 'elastic'
    elastic_host: str = 'http://elasticsearch:9200/'

    database_uri: str = 'sqlite+aiosqlite:///./data/memoria.db'

    import_threads: int = CPU_COUNT // 2 if CPU_COUNT is not None else 1

    downloader: str = 'AiohttpDownloader'
    extractor: str = 'HtmlExtractor'
    filter_stack: list[str] = ['HtmlContentFinder']

    allowlist: Path = './data/allowlist.txt'
    denylist: Path = './data/denylist.txt'

    @classmethod
    def settings_customise_sources(cls, _, init_settings, env_settings, dotenv_settings, file_secret_settings) -> tuple[PydanticBaseSettingsSource, ...]:
        return init_settings, file_secret_settings, env_settings, dotenv_settings


SETTINGS = Settings()
