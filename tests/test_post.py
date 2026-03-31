"""Test post selector calculations."""

import pytest
from post_selector import run_calculation, ClimaticLoads, POST_DATABASE


def test_4ply_2x8_at_4ft_spacing_passes():
    """4-ply 2x8 at 4ft spacing should pass for 80x250x20 building."""
    climate = ClimaticLoads(Ss=27.88 / 20.9, Sr=0.0, q=0.5, source="Manual Entry")
    result = run_calculation(
        manual_loads=climate,
        width_ft=80,
        length_ft=250,
        eave_height_ft=20,
        post_spacing_ft=4,
        roof_slope=4,
        dead_load_psf=10,
        importance="normal",
        plies=4,
        size="2x8",
    )
    assert result.capacity.is_ok
    assert result.capacity.ratio_LC5 < 1.0


def test_3ply_2x8_at_8ft_spacing_fails():
    """3-ply 2x8 at 8ft spacing should fail for 80x250x20 building."""
    climate = ClimaticLoads(Ss=27.88 / 20.9, Sr=0.0, q=0.5, source="Manual Entry")
    result = run_calculation(
        manual_loads=climate,
        width_ft=80,
        length_ft=250,
        eave_height_ft=20,
        post_spacing_ft=8,
        roof_slope=4,
        dead_load_psf=10,
        importance="normal",
        plies=3,
        size="2x8",
    )
    assert not result.capacity.is_ok
    assert result.capacity.ratio_LC5 > 1.0


def test_all_posts_available():
    """All posts should be defined."""
    assert len(POST_DATABASE) == 4
    sizes = [(p.plies, p.size) for p in POST_DATABASE]
    assert (3, "2x6") in sizes
    assert (3, "2x8") in sizes
    assert (4, "2x6") in sizes
    assert (4, "2x8") in sizes


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
