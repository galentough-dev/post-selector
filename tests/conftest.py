"""Shared test fixtures."""

import pytest
from post_selector import ClimaticLoads, BuildingParams


@pytest.fixture
def heavy_climate():
    """Heavy climate loads (~1.33 kPa snow, 0.5 kPa wind)."""
    return ClimaticLoads(Ss=27.88 / 20.9, Sr=0.0, q=0.5, source="test")


@pytest.fixture
def typical_building(**overrides):
    """Standard 80x250x20 building with 4ft post spacing."""
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
