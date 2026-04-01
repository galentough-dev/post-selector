"""Test post selector calculations."""

import math
import pytest
from post_selector import (
    run_calculation,
    ClimaticLoads,
    BuildingParams,
    POST_DATABASE,
    calculate_snow_load,
    get_post,
    load_cities_from_csv,
    find_city,
    CityNotFoundError,
)
from post_selector.core import FT_TO_M


def _heavy_climate():
    return ClimaticLoads(Ss=27.88 / 20.9, Sr=0.0, q=0.5, source="test")


def _typical_building(**overrides):
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


class TestBuildingParams:
    def test_width_conversion(self):
        b = _typical_building(width_ft=80)
        assert abs(b.width_m - 80 * FT_TO_M) < 0.001

    def test_slope_degrees(self):
        b = _typical_building(roof_slope=4)
        assert abs(b.slope_degrees - math.degrees(math.atan(4 / 12.0))) < 0.01

    def test_negative_width_raises(self):
        with pytest.raises(ValueError, match="width_ft must be positive"):
            _typical_building(width_ft=-10)

    def test_zero_height_raises(self):
        with pytest.raises(ValueError, match="eave_height_ft must be positive"):
            _typical_building(eave_height_ft=0)

    def test_negative_slope_raises(self):
        with pytest.raises(ValueError, match="roof_slope must be non-negative"):
            _typical_building(roof_slope=-1)

    def test_invalid_importance_raises(self):
        with pytest.raises(ValueError, match="importance must be one of"):
            BuildingParams(
                width_ft=80,
                length_ft=250,
                eave_height_ft=20,
                post_spacing_ft=4,
                roof_slope=4,
                dead_load_psf=10,
                importance="invalid",
            )

    def test_roof_height_calculation(self):
        b = _typical_building(width_ft=80, eave_height_ft=20, roof_slope=4)
        expected = 20 + (4 / 12) * (80 / 2)
        assert abs(b.roof_height_ft - expected) < 0.001

    def test_reference_height_is_average(self):
        b = _typical_building(eave_height_ft=20, roof_slope=4)
        assert (
            abs(b.reference_height_ft - (b.eave_height_ft + b.roof_height_ft) / 2)
            < 0.001
        )


class TestSnowLoad:
    def test_flat_roof_Cs_is_1(self):
        climate = _heavy_climate()
        building = _typical_building(roof_slope=0)
        snow = calculate_snow_load(climate, building, roof_type="unobstructed_slippery")
        assert snow.Cs == 1.0

    def test_steep_slippery_roof_Cs_is_0(self):
        climate = _heavy_climate()
        building = _typical_building(roof_slope=21)
        alpha = math.degrees(math.atan(21 / 12.0))
        assert alpha >= 60
        snow = calculate_snow_load(climate, building, roof_type="unobstructed_slippery")
        assert snow.Cs == 0.0

    def test_exposed_reduces_load(self):
        climate = _heavy_climate()
        building = _typical_building()
        s_sheltered = calculate_snow_load(climate, building, exposure="sheltered")
        s_exposed = calculate_snow_load(climate, building, exposure="exposed")
        assert s_exposed.S_balanced < s_sheltered.S_balanced

    def test_design_is_max_of_balanced_unbalanced(self):
        climate = _heavy_climate()
        building = _typical_building()
        result = calculate_snow_load(climate, building)
        assert result.S_design == max(result.S_balanced, result.S_unbalanced)

    def test_Cb_always_0_8(self):
        result = calculate_snow_load(_heavy_climate(), _typical_building())
        assert result.Cb == 0.8


class TestWindLoad:
    def test_exposed_Ce_greater_than_sheltered(self):
        from post_selector import calculate_wind_load

        climate = _heavy_climate()
        building = _typical_building()
        r_exp = calculate_wind_load(climate, building, exposure="exposed")
        r_shl = calculate_wind_load(climate, building, exposure="sheltered")
        assert r_exp.Ce > r_shl.Ce

    def test_wall_pressure_positive(self):
        from post_selector import calculate_wind_load

        result = calculate_wind_load(_heavy_climate(), _typical_building())
        assert result.wall_wind_load > 0

    def test_psf_conversion(self):
        from post_selector import calculate_wind_load
        from post_selector import PSF_TO_KPA

        result = calculate_wind_load(_heavy_climate(), _typical_building())
        assert abs(result.wall_wind_psf - result.wall_wind_load * PSF_TO_KPA) < 0.01


class TestPostDatabase:
    def test_all_posts_available(self):
        assert len(POST_DATABASE) == 4
        sizes = [(p.plies, p.size) for p in POST_DATABASE]
        assert (3, "2x6") in sizes
        assert (3, "2x8") in sizes
        assert (4, "2x6") in sizes
        assert (4, "2x8") in sizes

    def test_get_post_valid(self):
        post = get_post(4, "2x8")
        assert post.plies == 4
        assert post.size == "2x8"

    def test_get_post_invalid(self):
        with pytest.raises(ValueError, match="Post not found"):
            get_post(5, "2x10")


class TestInputValidation:
    def test_invalid_plies(self):
        with pytest.raises(ValueError, match="plies must be one of"):
            run_calculation(manual_loads=_heavy_climate(), plies=5, size="2x6")

    def test_invalid_size(self):
        with pytest.raises(ValueError, match="size must be one of"):
            run_calculation(manual_loads=_heavy_climate(), plies=4, size="2x10")


class TestRunCalculation:
    def test_4ply_2x8_at_4ft_passes(self):
        climate = _heavy_climate()
        result = run_calculation(
            manual_loads=climate,
            width_ft=80,
            length_ft=250,
            eave_height_ft=20,
            post_spacing_ft=4,
            roof_slope=4,
            dead_load_psf=10,
            plies=4,
            size="2x8",
        )
        assert result.capacity.is_ok
        assert result.capacity.ratio_LC5 < 1.0

    def test_3ply_2x8_at_8ft_fails(self):
        climate = _heavy_climate()
        result = run_calculation(
            manual_loads=climate,
            width_ft=80,
            length_ft=250,
            eave_height_ft=20,
            post_spacing_ft=8,
            roof_slope=4,
            dead_load_psf=10,
            plies=3,
            size="2x8",
        )
        assert not result.capacity.is_ok
        assert result.capacity.ratio_LC5 > 1.0

    def test_no_climate_source_raises(self):
        with pytest.raises(ValueError, match="Must provide"):
            run_calculation(width_ft=80, plies=4, size="2x6")


class TestCitySearch:
    @pytest.fixture(autouse=True)
    def load_db(self):
        load_cities_from_csv()

    def test_exact_match(self):
        city = find_city("Edmonton")
        assert city is not None
        assert "Edmonton" in city[0]

    def test_partial_match(self):
        city = find_city("Calgary")
        assert city is not None
        assert "Calgary" in city[0]

    def test_nonexistent_returns_none(self):
        city = find_city("ZZZZZZZZZ")
        assert city is None

    def test_from_nbcc_city_not_found(self):
        with pytest.raises(CityNotFoundError):
            ClimaticLoads.from_nbcc_city("ZZZZZZZZZ")


class TestCapacityResult:
    def test_is_ok_when_both_pass(self):
        result = run_calculation(
            manual_loads=_heavy_climate(),
            width_ft=80,
            length_ft=250,
            eave_height_ft=20,
            post_spacing_ft=4,
            roof_slope=4,
            dead_load_psf=10,
            plies=4,
            size="2x8",
        )
        assert result.capacity.is_ok is True

    def test_is_ok_false_when_fails(self):
        result = run_calculation(
            manual_loads=ClimaticLoads(Ss=10.0, Sr=0.0, q=2.0, source="extreme"),
            width_ft=80,
            length_ft=250,
            eave_height_ft=20,
            post_spacing_ft=8,
            roof_slope=4,
            dead_load_psf=10,
            plies=3,
            size="2x6",
        )
        assert result.capacity.is_ok is False


class TestSummary:
    def test_summary_contains_key_info(self):
        result = run_calculation(
            manual_loads=_heavy_climate(),
            width_ft=80,
            length_ft=250,
            eave_height_ft=20,
            post_spacing_ft=4,
            roof_slope=4,
            dead_load_psf=10,
            plies=4,
            size="2x8",
        )
        summary = result.summary()
        assert "POST SELECTOR" in summary
        assert "LC3" in summary
        assert "LC5" in summary
        assert "POST IS OK" in summary or "POST IS INADEQUATE" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
