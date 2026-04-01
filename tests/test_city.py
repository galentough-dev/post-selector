"""Test city database and search functionality."""

import pytest
from unittest.mock import patch
from post_selector import (
    load_cities_from_csv,
    find_city,
    get_city_db,
    CityNotFoundError,
    AmbiguousCityError,
    ClimaticLoads,
)


@pytest.fixture(autouse=True)
def loaded_db():
    load_cities_from_csv()


class TestCityDatabase:
    def test_db_has_cities(self):
        db = get_city_db()
        assert len(db) > 0

    def test_db_entry_structure(self):
        db = get_city_db()
        for city in db:
            assert len(city) == 5
            label, Ss, Sr, q10, q50 = city
            assert isinstance(label, str)
            assert Ss >= 0
            assert Sr >= 0
            assert q10 >= 0
            assert q50 >= 0


class TestFindCity:
    def test_exact_name_match(self):
        city = find_city("Edmonton")
        assert city is not None
        assert "Edmonton" in city[0]

    def test_case_insensitive(self):
        city = find_city("edmonton")
        assert city is not None

    def test_partial_name(self):
        city = find_city("Grande Prairie")
        assert city is not None
        assert "Grande Prairie" in city[0]

    def test_not_found_returns_none(self):
        city = find_city("NonexistentCityXYZ123")
        assert city is None

    def test_empty_db_returns_none(self):
        from post_selector import core

        with patch.object(core, "load_cities_from_csv"):
            core._CITY_DB.clear()
            city = find_city("Edmonton")
            assert city is None


class TestClimaticLoadsFromCity:
    def test_from_nbcc_city_success(self):
        climate = ClimaticLoads.from_nbcc_city("Edmonton")
        assert climate.Ss > 0
        assert "NBCC-2010" in climate.source

    def test_from_nbcc_city_not_found(self):
        with pytest.raises(CityNotFoundError):
            ClimaticLoads.from_nbcc_city("NonexistentCityXYZ123")

    def test_low_importance_uses_q10(self):
        climate_low = ClimaticLoads.from_nbcc_city("Edmonton", importance="low")
        climate_normal = ClimaticLoads.from_nbcc_city("Edmonton", importance="normal")
        assert climate_low.q <= climate_normal.q
