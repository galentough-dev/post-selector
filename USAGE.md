# Post Selector - Usage Guide

## Quick Start

```bash
cd C:\Users\galen\post_selector
pip install -e .
```

## CLI Commands

### Basic Calculation
```bash
post-selector --city "CITY NAME" --width WIDTH --height HEIGHT --spacing SPACING --plies PLYS --size SIZE
```

### Example - Hardisty, AB Building
```bash
# 80' wide, 250' long, 20' eave height, 4-ply 2x8 @ 4ft spacing
post-selector --city "Hardisty" --width 80 --length 250 --height 20 --spacing 4 --plies 4 --size 2x8
```

## Parameters

| Parameter | Flag | Default | Description |
|-----------|------|---------|-------------|
| City | `--city` | required | NBCC location name |
| Width | `--width` | 32 | Building width (ft) |
| Length | `--length` | 40 | Building length (ft) |
| Height | `--height` | 12 | Eave height (ft) |
| Spacing | `--spacing` | 8 | Post spacing (ft) |
| Slope | `--slope` | 4 | Roof slope (x:12) |
| Dead load | `--dead` | 10 | Dead load (psf) |
| Plies | `--plies` | 4 | Number of plies (3 or 4) |
| Size | `--size` | 2x6 | Post size (2x6 or 2x8) |
| Importance | `--importance` | normal | low, normal, high, post_disaster |
| Snow exposure | `--snow-exposure` | sheltered | sheltered, exposed, exposed_north |
| Wind exposure | `--wind-exposure` | exposed | exposed, sheltered |

## Information Commands

```bash
# List all available provinces/regions
post-selector --list-regions

# List cities (optionally filter by name)
post-selector --list-cities
post-selector --list-cities "Alberta"
post-selector --list-cities "Calgary"

# List available post sizes
post-selector --list-posts

# Run validation tests
post-selector --validate
```

## Available Posts

| Post | Mr (kN-m) | fc (MPa) | Area (mm²) |
|------|-----------|----------|------------|
| 3-ply 2x6 | 5.49 | 11.5 | 15,960 |
| 3-ply 2x8 | 6.33 | 11.5 | 20,976 |
| 4-ply 2x6 | 6.86 | 11.5 | 21,280 |
| 4-ply 2x8 | 10.46 | 11.5 | 27,968 |

## Maximum Spacing Guide

For typical buildings (80' wide, 20' eave height):

### Hardisty, AB (Ss=1.7 kPa, q=0.36 kPa)
| Post | Max Spacing | LC5 Ratio |
|------|-------------|-----------|
| 3-ply 2x8 | 4.5' o.c. | 0.94 |
| 4-ply 2x8 | 6' o.c. | 0.98 |

### Grande Prairie, AB (Ss=2.2 kPa, q=0.43 kPa)
| Post | Max Spacing | LC5 Ratio |
|------|-------------|-----------|
| 3-ply 2x8 | 4' o.c. | 0.84 |
| 4-ply 2x8 | 6' o.c. | 0.98 |

## Python API

```python
from post_selector import run_calculation, load_cities_from_csv

# Load city database
load_cities_from_csv()

# Run calculation
result = run_calculation(
    city_name="Edmonton",
    width_ft=80,
    length_ft=250,
    eave_height_ft=20,
    post_spacing_ft=4,
    roof_slope=4,
    dead_load_psf=10,
    plies=4,
    size="2x8",
)

# Get results
print(f"Snow load: {result.snow.S_design:.2f} kPa")
print(f"Wind pressure: {result.wind.wall_wind_load:.2f} kPa")
print(f"LC3 ratio: {result.capacity.ratio_LC3:.3f}")
print(f"LC5 ratio: {result.capacity.ratio_LC5:.3f}")
print(f"Status: {'PASS' if result.capacity.is_ok else 'FAIL'}")
```

## Finding Maximum Spacing

```python
from post_selector import run_calculation, load_cities_from_csv

load_cities_from_csv()

city = "Hardisty"
plies = 3
size = "2x8"

# Binary search for max spacing
for spacing in [3.0, 3.5, 4.0, 4.5, 5.0]:
    result = run_calculation(
        city_name=city,
        width_ft=80, length_ft=250, eave_height_ft=20,
        post_spacing_ft=spacing,
        plies=plies, size=size,
    )
    status = "PASS" if result.capacity.is_ok else "FAIL"
    print(f"{spacing}ft spacing: LC5={result.capacity.ratio_LC5:.3f} [{status}]")
```

## Design Codes

- **NBCC-2010** Division B, Sections 4.1.6 (Snow) and 4.1.7 (Wind)
- **CSA O86-09** Engineering Design in Wood
- **ASABE EP486.1** Shallow Post Foundation Design
- **NDS AWC DA6** Post-frame bending model

## Load Combinations

| Load Case | Combination |
|-----------|-------------|
| LC3 | 1.25D + 1.5S + 0.4W |
| LC5 | 1.25D + 1.4W + 0.5S |

## Troubleshooting

### City not found
```bash
# Search for city
post-selector --list-cities "partial name"
```

### Import error
```bash
# Reinstall package
cd C:\Users\galen\post_selector
pip install -e .
```

### Unicode error on Windows
The CLI uses ASCII characters for compatibility. Unicode symbols were removed from output.