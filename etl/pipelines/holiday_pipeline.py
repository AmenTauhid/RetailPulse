"""Fetch Canadian public holidays from Nager.Date API."""

import logging
from datetime import date

import httpx
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from data.scripts.db.models import Holiday

logger = logging.getLogger(__name__)

NAGER_DATE_URL = "https://date.nager.at/api/v3/PublicHolidays/{year}/CA"

# Map Nager.Date county codes to Canadian province codes
COUNTY_TO_PROVINCE: dict[str, str] = {
    "CA-AB": "AB",
    "CA-BC": "BC",
    "CA-MB": "MB",
    "CA-NB": "NB",
    "CA-NL": "NL",
    "CA-NS": "NS",
    "CA-NT": "NT",
    "CA-NU": "NU",
    "CA-ON": "ON",
    "CA-PE": "PE",
    "CA-QC": "QC",
    "CA-SK": "SK",
    "CA-YT": "YT",
}


def fetch_holidays_for_year(year: int) -> list[dict]:
    """Fetch holidays from Nager.Date API for a given year."""
    url = NAGER_DATE_URL.format(year=year)
    try:
        response = httpx.get(url, timeout=10.0)
        response.raise_for_status()
        return response.json()
    except httpx.HTTPError as e:
        logger.error("Failed to fetch holidays for %d: %s", year, e)
        return []


def parse_holidays(raw_holidays: list[dict]) -> list[dict]:
    """Parse Nager.Date API response into holiday records."""
    records: list[dict] = []
    for h in raw_holidays:
        provinces = h.get("counties") or [None]
        for county in provinces:
            province_code = COUNTY_TO_PROVINCE.get(county) if county else None
            records.append(
                {
                    "date": date.fromisoformat(h["date"]),
                    "name": h["localName"],
                    "country_code": "CA",
                    "province_code": province_code,
                    "is_public": h.get("global", True),
                    "holiday_type": h.get("types", ["Public"])[0] if h.get("types") else "Public",
                }
            )
    return records


def load_holidays(session: Session, start_year: int, end_year: int) -> int:
    """Fetch and upsert holidays for the given year range.

    Returns the number of holidays inserted.
    """
    total_inserted = 0

    for year in range(start_year, end_year + 1):
        logger.info("Fetching holidays for %d...", year)
        raw = fetch_holidays_for_year(year)
        if not raw:
            logger.warning("No holidays returned for %d", year)
            continue

        records = parse_holidays(raw)
        for record in records:
            stmt = (
                pg_insert(Holiday)
                .values(**record)
                .on_conflict_do_nothing(constraint="uq_holiday_date_name_province")
            )
            session.execute(stmt)
            total_inserted += 1

        session.commit()
        logger.info("Loaded %d holiday records for %d", len(records), year)

    return total_inserted
