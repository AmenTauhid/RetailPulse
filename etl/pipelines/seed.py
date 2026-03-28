"""Seed orchestrator: populates the database from scratch with synthetic + real data.

Usage:
    python -m etl.pipelines.seed

Steps (in dependency order):
    1. Create all tables
    2. Insert stores
    3. Insert categories and products
    4. Generate and insert synthetic weather
    5. Generate and insert synthetic events
    6. Fetch and insert real holidays (Nager.Date API)
    7. Generate and insert transactions (depends on weather + holidays)
    8. Compute and insert daily aggregates
"""

import logging
import sys
from datetime import date

from sqlalchemy import func, select

from data.scripts.db.base import Base, get_engine
from data.scripts.db.models import (
    Category,
    DailyAggregate,
    Event,
    Holiday,
    Product,
    Store,
    Transaction,
    WeatherDaily,
)
from data.scripts.db.session import get_session_factory
from data.scripts.generate_aggregates import generate_aggregates
from data.scripts.generate_events import generate_events
from data.scripts.generate_products import generate_categories, generate_products
from data.scripts.generate_stores import generate_stores
from data.scripts.generate_transactions import generate_transactions
from data.scripts.generate_weather import generate_weather
from etl.pipelines.config import get_settings
from etl.pipelines.holiday_pipeline import load_holidays

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


def _table_count(session, model) -> int:
    """Return row count for a table."""
    return session.scalar(select(func.count()).select_from(model))


def seed():
    """Run the full seed pipeline."""
    settings = get_settings()
    engine = get_engine()
    SessionFactory = get_session_factory()

    start_date = date.fromisoformat(settings.data_start_date)
    end_date = date.fromisoformat(settings.data_end_date)

    logger.info("=" * 60)
    logger.info("RetailPulse Database Seed")
    logger.info("Date range: %s to %s", start_date, end_date)
    logger.info("=" * 60)

    # Step 1: Create tables
    logger.info("Step 1/8: Creating tables...")
    Base.metadata.create_all(engine)
    logger.info("  Tables created.")

    with SessionFactory() as session:
        # Step 2: Stores
        if _table_count(session, Store) > 0:
            logger.info(
                "Step 2/8: Stores already seeded (%d rows). Skipping.", _table_count(session, Store)
            )
        else:
            logger.info("Step 2/8: Inserting stores...")
            stores = generate_stores()
            session.add_all(stores)
            session.commit()
            logger.info("  Inserted %d stores.", len(stores))

        stores = list(session.scalars(select(Store)).all())

        # Step 3: Categories + Products
        if _table_count(session, Category) > 0:
            logger.info("Step 3/8: Categories/products already seeded. Skipping.")
        else:
            logger.info("Step 3/8: Inserting categories and products...")
            categories = generate_categories()
            session.add_all(categories)
            session.commit()

            categories = list(session.scalars(select(Category)).all())
            products = generate_products(categories)
            session.add_all(products)
            session.commit()
            logger.info("  Inserted %d categories and %d products.", len(categories), len(products))

        categories = list(session.scalars(select(Category)).all())
        products = list(session.scalars(select(Product)).all())

        # Step 4: Synthetic weather
        if _table_count(session, WeatherDaily) > 0:
            logger.info(
                "Step 4/8: Weather data already seeded (%d rows). Skipping.",
                _table_count(session, WeatherDaily),
            )
        else:
            logger.info("Step 4/8: Generating synthetic weather data...")
            weather_records = generate_weather(stores, start_date, end_date)
            # Batch insert for performance
            batch_size = 5000
            for i in range(0, len(weather_records), batch_size):
                session.add_all(weather_records[i : i + batch_size])
                session.commit()
            logger.info("  Inserted %d weather records.", len(weather_records))

        # Step 5: Synthetic events
        if _table_count(session, Event) > 0:
            logger.info(
                "Step 5/8: Events already seeded (%d rows). Skipping.", _table_count(session, Event)
            )
        else:
            logger.info("Step 5/8: Generating synthetic events...")
            events = generate_events(start_date, end_date)
            session.add_all(events)
            session.commit()
            logger.info("  Inserted %d events.", len(events))

        # Step 6: Real holidays from Nager.Date API
        if _table_count(session, Holiday) > 0:
            logger.info(
                "Step 6/8: Holidays already seeded (%d rows). Skipping.",
                _table_count(session, Holiday),
            )
        else:
            logger.info("Step 6/8: Fetching holidays from Nager.Date API...")
            count = load_holidays(session, start_date.year, end_date.year)
            logger.info("  Loaded %d holiday records.", count)

        holidays = list(session.scalars(select(Holiday)).all())

        # Step 7: Transactions
        if _table_count(session, Transaction) > 0:
            logger.info(
                "Step 7/8: Transactions already seeded (%d rows). Skipping.",
                _table_count(session, Transaction),
            )
        else:
            logger.info("Step 7/8: Generating transactions (this may take a moment)...")
            # Build weather lookup
            weather_all = session.scalars(select(WeatherDaily)).all()
            weather_map = {(w.store_id, w.date): w for w in weather_all}

            txns = generate_transactions(
                stores,
                products,
                categories,
                weather_map,
                holidays,
                start_date,
                end_date,
            )
            logger.info("  Generated %d transactions. Inserting in batches...", len(txns))

            batch_size = 10000
            for i in range(0, len(txns), batch_size):
                session.add_all(txns[i : i + batch_size])
                session.commit()
                if (i // batch_size) % 10 == 0:
                    logger.info(
                        "    Inserted %d / %d...", min(i + batch_size, len(txns)), len(txns)
                    )
            logger.info("  Inserted %d transactions.", len(txns))

        # Step 8: Daily aggregates
        if _table_count(session, DailyAggregate) > 0:
            logger.info(
                "Step 8/8: Aggregates already seeded (%d rows). Skipping.",
                _table_count(session, DailyAggregate),
            )
        else:
            logger.info("Step 8/8: Computing daily aggregates...")
            txns = list(session.scalars(select(Transaction)).all())
            aggs = generate_aggregates(txns, products)

            batch_size = 5000
            for i in range(0, len(aggs), batch_size):
                session.add_all(aggs[i : i + batch_size])
                session.commit()
            logger.info("  Inserted %d aggregate records.", len(aggs))

    # Summary
    logger.info("")
    logger.info("=" * 60)
    logger.info("Seed complete! Table summary:")
    with SessionFactory() as session:
        for model in [
            Store,
            Category,
            Product,
            WeatherDaily,
            Event,
            Holiday,
            Transaction,
            DailyAggregate,
        ]:
            count = _table_count(session, model)
            logger.info("  %-20s %s rows", model.__tablename__, f"{count:,}")
    logger.info("=" * 60)


if __name__ == "__main__":
    seed()
