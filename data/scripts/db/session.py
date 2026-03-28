from sqlalchemy.orm import Session, sessionmaker

from data.scripts.db.base import get_engine


def get_session_factory(url: str | None = None) -> sessionmaker[Session]:
    """Create a sync session factory."""
    engine = get_engine(url)
    return sessionmaker(bind=engine, expire_on_commit=False)
