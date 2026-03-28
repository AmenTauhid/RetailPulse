from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase

from etl.pipelines.config import get_settings


class Base(DeclarativeBase):
    pass


def get_engine(url: str | None = None):
    """Create a sync SQLAlchemy engine."""
    if url is None:
        url = get_settings().database_url_sync
    return create_engine(url, echo=False, pool_size=5, max_overflow=10)
