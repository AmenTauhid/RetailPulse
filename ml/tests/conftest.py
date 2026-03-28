"""Test fixtures for ML pipeline tests."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from data.scripts.db.base import Base


@pytest.fixture(scope="session")
def engine():
    """Create an in-memory SQLite engine for testing."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    """Provide a transactional session that rolls back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    factory = sessionmaker(bind=connection)
    session = factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
