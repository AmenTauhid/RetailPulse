"""Tests for the holiday pipeline."""

from datetime import date
from unittest.mock import MagicMock, patch

from etl.pipelines.holiday_pipeline import fetch_holidays_for_year, parse_holidays


class TestFetchHolidays:
    @patch("etl.pipelines.holiday_pipeline.httpx.get")
    def test_successful_fetch(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "date": "2024-01-01",
                "localName": "New Year's Day",
                "name": "New Year's Day",
                "countryCode": "CA",
                "global": True,
                "counties": None,
                "types": ["Public"],
            }
        ]
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        result = fetch_holidays_for_year(2024)
        assert len(result) == 1
        assert result[0]["localName"] == "New Year's Day"

    @patch("etl.pipelines.holiday_pipeline.httpx.get")
    def test_handles_api_error(self, mock_get):
        import httpx
        mock_get.side_effect = httpx.HTTPError("Connection failed")

        result = fetch_holidays_for_year(2024)
        assert result == []


class TestParseHolidays:
    def test_parses_national_holiday(self):
        raw = [
            {
                "date": "2024-07-01",
                "localName": "Canada Day",
                "global": True,
                "counties": None,
                "types": ["Public"],
            }
        ]
        records = parse_holidays(raw)
        assert len(records) == 1
        assert records[0]["name"] == "Canada Day"
        assert records[0]["date"] == date(2024, 7, 1)
        assert records[0]["province_code"] is None
        assert records[0]["country_code"] == "CA"

    def test_parses_provincial_holiday(self):
        raw = [
            {
                "date": "2024-02-19",
                "localName": "Family Day",
                "global": False,
                "counties": ["CA-ON", "CA-BC", "CA-AB"],
                "types": ["Public"],
            }
        ]
        records = parse_holidays(raw)
        assert len(records) == 3
        provinces = {r["province_code"] for r in records}
        assert provinces == {"ON", "BC", "AB"}

    def test_handles_missing_types(self):
        raw = [
            {
                "date": "2024-12-25",
                "localName": "Christmas Day",
                "global": True,
                "counties": None,
            }
        ]
        records = parse_holidays(raw)
        assert len(records) == 1
        assert records[0]["holiday_type"] == "Public"
