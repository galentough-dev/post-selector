#!/usr/bin/env python3
"""CLI for Post Selector."""

import argparse
import sys

from . import __version__
from .core import (
    run_calculation,
    load_cities_from_csv,
    run_validation,
    POST_DATABASE,
    get_city_db,
    AmbiguousCityError,
    CityNotFoundError,
)


def list_cities(pattern=None):
    """List available cities, optionally filtered by pattern."""
    cities = sorted(get_city_db(), key=lambda x: x[0])

    if pattern:
        pattern_lower = pattern.lower()
        cities = [c for c in cities if pattern_lower in c[0].lower()]

    print(f"{'City':<35} {'Ss (kPa)':<12} {'Sr (kPa)':<12} {'q50 (kPa)':<12}")
    print("-" * 75)
    for city in cities[:50]:
        print(f"{city[0]:<35} {city[1]:<12.2f} {city[2]:<12.2f} {city[4]:<12.2f}")

    if len(cities) > 50:
        print(f"\n... and {len(cities) - 50} more. Use --city <pattern> to filter.")

    if len(cities) == 0:
        print("No cities found matching that pattern.")


def list_regions():
    """List available provinces/regions."""
    regions = set()
    for city in get_city_db():
        if ", " in city[0]:
            region = city[0].split(", ")[1]
            regions.add(region)

    print("Available regions:")
    for r in sorted(regions):
        count = sum(1 for c in get_city_db() if c[0].endswith(f", {r}"))
        print(f"  {r} ({count} locations)")


def main():
    parser = argparse.ArgumentParser(
        description="Laminated Timber Post Capacity Calculator (NBCC-2010, CSA O86-09)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  post-selector --city "Edmonton" --width 40 --height 14 --plies 4
  post-selector --city "Calgary" --list-cities
  post-selector --list-regions
  post-selector --validate
        """,
    )

    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    parser.add_argument("--validate", action="store_true", help="Run validation tests")
    parser.add_argument(
        "--list-posts", action="store_true", help="List available post sizes"
    )
    parser.add_argument(
        "--list-cities",
        nargs="?",
        const="",
        metavar="PATTERN",
        help="List cities (optional: filter by pattern)",
    )
    parser.add_argument(
        "--list-regions", action="store_true", help="List available provinces/regions"
    )

    parser.add_argument(
        "--city",
        type=str,
        metavar="NAME",
        help="City name for NBCC climatic data (e.g., 'Edmonton' or 'Calgary, AB')",
    )

    parser.add_argument("--width", type=float, default=32, help="Building width (ft)")
    parser.add_argument("--length", type=float, default=40, help="Building length (ft)")
    parser.add_argument("--height", type=float, default=12, help="Eave height (ft)")
    parser.add_argument("--spacing", type=float, default=8, help="Post spacing (ft)")
    parser.add_argument("--slope", type=float, default=4, help="Roof slope (x:12)")
    parser.add_argument("--dead", type=float, default=10, help="Dead load (psf)")

    parser.add_argument("--plies", type=int, default=4, help="Number of plies (3 or 4)")
    parser.add_argument(
        "--size", type=str, default="2x6", help="Post size (2x6 or 2x8)"
    )

    parser.add_argument(
        "--importance",
        type=str,
        default="normal",
        choices=["low", "normal", "high", "post_disaster"],
        help="Importance category",
    )

    parser.add_argument(
        "--snow-exposure",
        type=str,
        default="sheltered",
        choices=["sheltered", "exposed", "exposed_north"],
        help="Snow exposure",
    )
    parser.add_argument(
        "--wind-exposure",
        type=str,
        default="exposed",
        choices=["exposed", "sheltered"],
        help="Wind exposure",
    )

    args = parser.parse_args()

    if args.validate:
        run_validation()
        return 0

    if args.list_posts:
        print("Available Posts:")
        print("-" * 60)
        print(f"{'Post':<15} {'Mr (kN-m)':<12} {'fc (MPa)':<12} {'A (mm2)':<12}")
        print("-" * 60)
        for p in POST_DATABASE:
            print(
                f"{p.plies}-ply {p.size:<10} {p.Mr:<12.2f} {p.fc:<12.1f} {p.A:<12.0f}"
            )
        return 0

    if args.list_regions:
        list_regions()
        return 0

    if args.list_cities is not None:
        list_cities(args.list_cities if args.list_cities else None)
        return 0

    if not args.city:
        print("Error: --city is required for calculations.")
        print("Use --list-cities to see available locations.")
        return 1

    load_cities_from_csv()

    try:
        result = run_calculation(
            city_name=args.city,
            width_ft=args.width,
            length_ft=args.length,
            eave_height_ft=args.height,
            post_spacing_ft=args.spacing,
            roof_slope=args.slope,
            dead_load_psf=args.dead,
            importance=args.importance,
            plies=args.plies,
            size=args.size,
            snow_exposure=args.snow_exposure,
            wind_exposure=args.wind_exposure,
        )
    except AmbiguousCityError as e:
        print(f"Error: {e}")
        print("Please be more specific. Matching cities:")
        for m in e.matches:
            print(f"  {m[0]}")
        return 1
    except CityNotFoundError as e:
        print(f"Error: {e}")
        print("Use --list-cities to see available locations.")
        return 1

    print(result.summary())
    return 0 if result.capacity.is_ok else 1


if __name__ == "__main__":
    sys.exit(main())
