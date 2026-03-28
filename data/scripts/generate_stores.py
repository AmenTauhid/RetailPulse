"""Generate 10 Canadian retail stores across 5 cities with real coordinates."""

from datetime import date

from data.scripts.db.models import Store

STORES = [
    Store(
        store_code="CTC-001",
        name="Canadian Tire - Yonge & Eglinton",
        city="Toronto",
        province="ON",
        latitude=43.7066,
        longitude=-79.3985,
        store_type="standard",
        opened_date=date(2018, 3, 15),
    ),
    Store(
        store_code="CTC-002",
        name="Canadian Tire - Scarborough Town Centre",
        city="Toronto",
        province="ON",
        latitude=43.7751,
        longitude=-79.2579,
        store_type="warehouse",
        opened_date=date(2015, 9, 1),
    ),
    Store(
        store_code="CTC-003",
        name="Canadian Tire - Etobicoke",
        city="Toronto",
        province="ON",
        latitude=43.6426,
        longitude=-79.5492,
        store_type="standard",
        opened_date=date(2019, 6, 20),
    ),
    Store(
        store_code="CTC-004",
        name="Canadian Tire - Cambie & Broadway",
        city="Vancouver",
        province="BC",
        latitude=49.2634,
        longitude=-123.1152,
        store_type="standard",
        opened_date=date(2016, 4, 10),
    ),
    Store(
        store_code="CTC-005",
        name="Canadian Tire - Grandview",
        city="Vancouver",
        province="BC",
        latitude=49.2747,
        longitude=-123.0693,
        store_type="express",
        opened_date=date(2020, 1, 8),
    ),
    Store(
        store_code="CTC-006",
        name="Canadian Tire - Crowfoot",
        city="Calgary",
        province="AB",
        latitude=51.1237,
        longitude=-114.1594,
        store_type="warehouse",
        opened_date=date(2014, 11, 22),
    ),
    Store(
        store_code="CTC-007",
        name="Canadian Tire - Signal Hill",
        city="Calgary",
        province="AB",
        latitude=51.0160,
        longitude=-114.1506,
        store_type="standard",
        opened_date=date(2017, 7, 1),
    ),
    Store(
        store_code="CTC-008",
        name="Canadian Tire - Marche Central",
        city="Montreal",
        province="QC",
        latitude=45.5355,
        longitude=-73.6361,
        store_type="warehouse",
        opened_date=date(2013, 5, 18),
    ),
    Store(
        store_code="CTC-009",
        name="Canadian Tire - Pointe-Claire",
        city="Montreal",
        province="QC",
        latitude=45.4563,
        longitude=-73.8108,
        store_type="standard",
        opened_date=date(2016, 10, 3),
    ),
    Store(
        store_code="CTC-010",
        name="Canadian Tire - Merivale Road",
        city="Ottawa",
        province="ON",
        latitude=45.3418,
        longitude=-75.7271,
        store_type="standard",
        opened_date=date(2018, 8, 14),
    ),
]


def generate_stores() -> list[Store]:
    """Return list of Store ORM objects ready for insertion."""
    return STORES
