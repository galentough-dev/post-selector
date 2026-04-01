"""Test snow load calculations (NBCC-2010 4.1.6.2)."""

import math
import pytest
from post_selector import (
    ClimaticLoads,
    BuildingParams,
    calculate_snow_load,
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


def _climate(Ss=1.5, Sr=0.1, q=0.36):
    return ClimaticLoads(Ss=Ss, Sr=Sr, q=q, source="test")


class TestSnowCoefficients:
    def test_Cb_always_0_8(self):
        result = calculate_snow_load(_climate(), _building())
        assert result.Cb == 0.8

    def test_Cw_sheltered(self):
        result = calculate_snow_load(_climate(), _building(), exposure="sheltered")
        assert result.Cw == 1.0

    def test_Cw_exposed(self):
        result = calculate_snow_load(_climate(), _building(), exposure="exposed")
        assert result.Cw == 0.75

    def test_Cw_exposed_north(self):
        result = calculate_snow_load(_climate(), _building(), exposure="exposed_north")
        assert result.Cw == 0.5


class TestSlopeFactor:
    def test_flat_slippery_roof_Cs_is_1(self):
        b = _building(roof_slope=0)
        result = calculate_snow_load(_climate(), b, roof_type="unobstructed_slippery")
        assert result.Cs == 1.0

    def test_steep_slippery_roof_Cs_is_0(self):
        b = _building(roof_slope=21)
        alpha = math.degrees(math.atan(21 / 12.0))
        assert alpha >= 60
        result = calculate_snow_load(_climate(), b, roof_type="unobstructed_slippery")
        assert result.Cs == 0.0

    def test_moderate_slippery_slope_Cs_between_0_and_1(self):
        b = _building(roof_slope=8)
        result = calculate_snow_load(_climate(), b, roof_type="unobstructed_slippery")
        assert 0.0 < result.Cs < 1.0

    def test_non_slippery_flat_Cs_is_1(self):
        b = _building(roof_slope=4)
        alpha = math.degrees(math.atan(4 / 12.0))
        assert alpha < 30
        result = calculate_snow_load(_climate(), b, roof_type="other")
        assert result.Cs == 1.0

    def test_non_slippery_steep_Cs_is_0(self):
        b = _building(roof_slope=40)
        alpha = math.degrees(math.atan(40 / 12.0))
        assert alpha >= 70
        result = calculate_snow_load(_climate(), b, roof_type="other")
        assert result.Cs == 0.0

    def test_non_slippery_moderate_Cs_between_0_and_1(self):
        b = _building(roof_slope=12)
        result = calculate_snow_load(_climate(), b, roof_type="other")
        assert 0.0 < result.Cs < 1.0


class TestUnbalancedSnow:
    def test_flat_roof_no_unbalanced(self):
        b = _building(roof_slope=2)
        alpha = math.degrees(math.atan(2 / 12.0))
        assert alpha < 15
        result = calculate_snow_load(_climate(), b)
        assert result.Ca_unbalanced == 0.0

    def test_steep_roof_unbalanced_factor(self):
        b = _building(roof_slope=5)
        alpha = math.degrees(math.atan(5 / 12.0))
        assert alpha > 20
        result = calculate_snow_load(_climate(), b)
        assert result.Ca_unbalanced == 1.25

    def test_transition_zone_unbalanced(self):
        b = _building(roof_slope=4)
        alpha = math.degrees(math.atan(4 / 12.0))
        assert 15 <= alpha <= 20
        result = calculate_snow_load(_climate(), b)
        assert 0.0 < result.Ca_unbalanced < 1.25


class TestDesignSnowLoad:
    def test_design_is_max_of_balanced_and_unbalanced(self):
        b = _building(roof_slope=4)
        result = calculate_snow_load(_climate(Ss=2.0, Sr=0.2), b)
        assert result.S_design == max(result.S_balanced, result.S_unbalanced)

    def test_importance_factor_applied(self):
        b_normal = _building()
        b_high = _building(importance="high")
        r_normal = calculate_snow_load(_climate(), b_normal)
        r_high = calculate_snow_load(_climate(), b_high)
        assert r_high.S_balanced > r_normal.S_balanced

    def test_zero_Ss_gives_near_zero_balanced(self):
        result = calculate_snow_load(
            ClimaticLoads(Ss=0.0, Sr=0.0, q=0.0, source="test"), _building()
        )
        assert result.S_balanced == 0.0
