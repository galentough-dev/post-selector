"""Test wind load calculations (NBCC-2010 4.1.7.1)."""

import math
import pytest
from post_selector import (
    ClimaticLoads,
    BuildingParams,
    calculate_wind_load,
)


def _building(**overrides):
    defaults = dict(
        width_ft=80,
        length_ft=250,
        eave_height_ft=20,
        post_spacing_ft=4,
        roof_slope=4,
        dead_load_psf=10,
    )
    defaults.update(overrides)
    return BuildingParams(**defaults)


def _climate(q=0.5):
    return ClimaticLoads(Ss=1.5, Sr=0.1, q=q, source="test")


class TestWindExposureCoefficient:
    def test_exposed_Ce_minimum(self):
        b = _building(eave_height_ft=10)
        result = calculate_wind_load(_climate(), b, exposure="exposed")
        assert result.Ce >= 0.9

    def test_sheltered_Ce_minimum(self):
        b = _building(eave_height_ft=10)
        result = calculate_wind_load(_climate(), b, exposure="sheltered")
        assert result.Ce >= 0.7

    def test_exposed_Ce_increases_with_height(self):
        b_low = _building(eave_height_ft=12)
        b_high = _building(eave_height_ft=30)
        r_low = calculate_wind_load(_climate(), b_low, exposure="exposed")
        r_high = calculate_wind_load(_climate(), b_high, exposure="exposed")
        assert r_high.Ce > r_low.Ce


class TestWindPressures:
    def test_wall_pressure_positive(self):
        b = _building()
        result = calculate_wind_load(_climate(), b)
        assert result.wall_wind_load > 0

    def test_wall_psf_conversion(self):
        b = _building()
        result = calculate_wind_load(_climate(), b)
        assert abs(result.wall_wind_psf - result.wall_wind_load * 20.9) < 0.01

    def test_roof_psf_conversion(self):
        b = _building()
        result = calculate_wind_load(_climate(), b)
        assert abs(result.roof_wind_psf - result.roof_wind_load * 20.9) < 0.01

    def test_higher_q_gives_higher_pressure(self):
        b = _building()
        r_low = calculate_wind_load(_climate(q=0.3), b)
        r_high = calculate_wind_load(_climate(q=0.6), b)
        assert r_high.wall_wind_load > r_low.wall_wind_load

    def test_importance_factor_affects_pressure(self):
        b_normal = _building(importance="normal")
        b_high = _building(importance="high")
        r_normal = calculate_wind_load(_climate(), b_normal)
        r_high = calculate_wind_load(_climate(), b_high)
        assert r_high.wall_wind_load > r_normal.wall_wind_load
