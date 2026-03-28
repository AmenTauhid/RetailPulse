"""Tests for synthetic data generators."""

from datetime import date
from decimal import Decimal

from data.scripts.generate_aggregates import generate_aggregates
from data.scripts.generate_events import generate_events
from data.scripts.generate_products import generate_categories, generate_products
from data.scripts.generate_stores import generate_stores
from data.scripts.generate_transactions import generate_transactions
from data.scripts.generate_weather import generate_weather


class TestGenerateStores:
    def test_returns_10_stores(self):
        stores = generate_stores()
        assert len(stores) == 10

    def test_store_codes_are_unique(self):
        stores = generate_stores()
        codes = [s.store_code for s in stores]
        assert len(codes) == len(set(codes))

    def test_stores_have_valid_coordinates(self):
        stores = generate_stores()
        for store in stores:
            assert -90 <= float(store.latitude) <= 90
            assert -180 <= float(store.longitude) <= 180

    def test_cities_covered(self):
        stores = generate_stores()
        cities = {s.city for s in stores}
        assert cities == {"Toronto", "Vancouver", "Calgary", "Montreal", "Ottawa"}

    def test_store_types_are_valid(self):
        stores = generate_stores()
        valid_types = {"standard", "warehouse", "express"}
        for store in stores:
            assert store.store_type in valid_types


class TestGenerateProducts:
    def test_categories_count(self):
        categories = generate_categories()
        assert len(categories) == 14

    def test_category_names_are_unique(self):
        categories = generate_categories()
        names = [c.name for c in categories]
        assert len(names) == len(set(names))

    def test_seasonal_categories_have_peak_season(self):
        categories = generate_categories()
        for cat in categories:
            if cat.is_seasonal:
                assert cat.peak_season in ("winter", "summer", "spring", "fall")
            else:
                assert cat.peak_season is None

    def test_products_linked_to_categories(self, session):
        categories = generate_categories()
        session.add_all(categories)
        session.flush()

        products = generate_products(categories)
        assert len(products) > 40  # At least 40 products

        cat_ids = {c.id for c in categories}
        for product in products:
            assert product.category_id in cat_ids

    def test_product_skus_are_unique(self, session):
        categories = generate_categories()
        session.add_all(categories)
        session.flush()

        products = generate_products(categories)
        skus = [p.sku for p in products]
        assert len(skus) == len(set(skus))

    def test_product_prices_positive(self, session):
        categories = generate_categories()
        session.add_all(categories)
        session.flush()

        products = generate_products(categories)
        for p in products:
            assert p.unit_price > 0
            assert p.unit_cost > 0
            assert p.unit_cost < p.unit_price


class TestGenerateWeather:
    def test_generates_records_for_all_stores(self):
        stores = generate_stores()
        # Assign fake IDs
        for i, s in enumerate(stores, 1):
            s.id = i

        weather = generate_weather(stores, date(2024, 1, 1), date(2024, 1, 31))
        store_ids = {w.store_id for w in weather}
        assert store_ids == {s.id for s in stores}

    def test_one_record_per_store_per_day(self):
        stores = generate_stores()
        for i, s in enumerate(stores, 1):
            s.id = i

        start = date(2024, 1, 1)
        end = date(2024, 1, 10)
        weather = generate_weather(stores, start, end)

        # 10 stores × 10 days = 100 records
        assert len(weather) == 10 * 10

    def test_winter_temps_are_cold(self):
        stores = [s for s in generate_stores() if s.city == "Toronto"]
        stores[0].id = 1

        weather = generate_weather(stores[:1], date(2024, 1, 1), date(2024, 1, 31))
        mean_temps = [float(w.temp_mean_c) for w in weather]
        avg_jan_temp = sum(mean_temps) / len(mean_temps)

        # Toronto January should average roughly -5 to 0 with noise
        assert avg_jan_temp < 5

    def test_summer_temps_are_warm(self):
        stores = [s for s in generate_stores() if s.city == "Toronto"]
        stores[0].id = 1

        weather = generate_weather(stores[:1], date(2024, 7, 1), date(2024, 7, 31))
        mean_temps = [float(w.temp_mean_c) for w in weather]
        avg_jul_temp = sum(mean_temps) / len(mean_temps)

        # Toronto July should average roughly 18-25
        assert avg_jul_temp > 15


class TestGenerateEvents:
    def test_generates_events_in_date_range(self):
        events = generate_events(date(2024, 1, 1), date(2024, 12, 31))
        assert len(events) > 50  # Should have many events

        for event in events:
            assert event.start_date >= date(2024, 1, 1)
            assert event.start_date <= date(2024, 12, 31)

    def test_events_cover_all_cities(self):
        events = generate_events(date(2024, 1, 1), date(2024, 12, 31))
        cities = {e.city for e in events}
        assert cities == {"Toronto", "Vancouver", "Calgary", "Montreal", "Ottawa"}

    def test_event_types_are_valid(self):
        events = generate_events(date(2024, 1, 1), date(2024, 12, 31))
        valid_types = {"sports", "festival", "concert"}
        for event in events:
            assert event.event_type in valid_types


class TestGenerateTransactions:
    def test_all_quantities_positive(self):
        stores = generate_stores()
        for i, s in enumerate(stores, 1):
            s.id = i

        categories = generate_categories()
        for i, c in enumerate(categories, 1):
            c.id = i

        products = generate_products(categories)
        for i, p in enumerate(products, 1):
            p.id = i

        # Use a very short range to keep test fast
        weather = generate_weather(stores[:1], date(2024, 6, 1), date(2024, 6, 3))
        weather_map = {(w.store_id, w.date): w for w in weather}

        txns = generate_transactions(
            stores[:1],
            products[:3],
            categories,
            weather_map,
            [],
            date(2024, 6, 1),
            date(2024, 6, 3),
        )
        for txn in txns:
            assert txn.quantity > 0
            assert txn.total_amount > 0

    def test_winter_products_peak_in_winter(self):
        """Winter product demand should be higher in January than July."""
        stores = generate_stores()
        stores[0].id = 1  # Just use one store

        categories = generate_categories()
        for i, c in enumerate(categories, 1):
            c.id = i

        products = generate_products(categories)
        for i, p in enumerate(products, 1):
            p.id = i

        # Get winter tire products
        winter_cat = next(c for c in categories if c.name == "Winter Tires")
        winter_products = [p for p in products if p.category_id == winter_cat.id]

        # Generate weather for January and July
        jan_weather = generate_weather([stores[0]], date(2024, 1, 1), date(2024, 1, 31))
        jul_weather = generate_weather([stores[0]], date(2024, 7, 1), date(2024, 7, 31))

        jan_map = {(w.store_id, w.date): w for w in jan_weather}
        jul_map = {(w.store_id, w.date): w for w in jul_weather}

        jan_txns = generate_transactions(
            [stores[0]],
            winter_products,
            categories,
            jan_map,
            [],
            date(2024, 1, 1),
            date(2024, 1, 31),
        )
        jul_txns = generate_transactions(
            [stores[0]],
            winter_products,
            categories,
            jul_map,
            [],
            date(2024, 7, 1),
            date(2024, 7, 31),
        )

        jan_qty = sum(t.quantity for t in jan_txns)
        jul_qty = sum(t.quantity for t in jul_txns)

        assert jan_qty > jul_qty, (
            f"Winter tires should sell more in Jan ({jan_qty}) than Jul ({jul_qty})"
        )


class TestGenerateAggregates:
    def test_aggregates_sum_correctly(self):
        from data.scripts.db.models import Product, Transaction

        products = [
            Product(
                id=1,
                sku="T1",
                name="P1",
                category_id=1,
                unit_price=Decimal("10.00"),
                unit_cost=Decimal("5.00"),
            ),
            Product(
                id=2,
                sku="T2",
                name="P2",
                category_id=1,
                unit_price=Decimal("20.00"),
                unit_cost=Decimal("10.00"),
            ),
        ]
        txns = [
            Transaction(
                store_id=1,
                product_id=1,
                transaction_date=date(2024, 1, 1),
                quantity=3,
                unit_price=Decimal("10.00"),
                total_amount=Decimal("30.00"),
            ),
            Transaction(
                store_id=1,
                product_id=2,
                transaction_date=date(2024, 1, 1),
                quantity=2,
                unit_price=Decimal("20.00"),
                total_amount=Decimal("40.00"),
            ),
        ]

        aggs = generate_aggregates(txns, products)
        assert len(aggs) == 1  # Same store, category, date
        assert aggs[0].total_quantity == 5
        assert aggs[0].total_revenue == Decimal("70.00")
        assert aggs[0].transaction_count == 2
