"""App settings, read from environment variables (see .env.example)."""

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Query options DigitalOcean adds to its MySQL URLs that PyMySQL does not understand.
_DROP_QUERY_KEYS = {"ssl-mode", "sslmode", "ssl_mode"}


def normalise_database_url(url: str) -> str:
    """Turn `mysql://...` (as DigitalOcean provides it) into a SQLAlchemy PyMySQL URL."""
    url = url.strip()
    if url.startswith("mysql://"):
        url = "mysql+pymysql://" + url[len("mysql://") :]
    parts = urlsplit(url)
    query = [(k, v) for k, v in parse_qsl(parts.query) if k.lower() not in _DROP_QUERY_KEYS]
    if not any(k == "charset" for k, _ in query):
        query.append(("charset", "utf8mb4"))
    return urlunsplit(parts._replace(query=urlencode(query)))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "mysql+pymysql://pte:pte@localhost:3306/pte"
    database_ca_cert: str | None = None
    db_pool_recycle: int = 1800
    db_pool_size: int = 5

    jwt_secret: str = "change-me-in-production"
    jwt_expire_hours: int = 24 * 7
    cookie_secure: bool = True
    cookie_name: str = "pte_session"

    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-5"
    # Only needed when the API key belongs to the whole account instead of one workspace.
    anthropic_workspace_id: str | None = None
    feedback_daily_limit: int = 30

    questions_per_set: int = 15
    # Speeds up mock test clocks for end-to-end tests. Keep at 1.0 in real use.
    mock_time_scale: float = 1.0
    min_active_per_type: int = 30
    recent_sets_excluded: int = 3
    report_retire_threshold: int = 3

    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def _normalise_url(cls, value: str) -> str:
        return normalise_database_url(value)

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
