# Post Selector

Laminated Timber Post Capacity Calculator per NBCC-2010 and CSA O86-09.

## Installation

```bash
cd C:\Users\galen\post_selector
pip install -e .
pip install -e ".[web]"  # For web interface
```

## Web Interface

```bash
# Launch clean, intuitive web UI
streamlit run post_selector/app.py
```

Opens at http://localhost:8501

Features:
- City search and selection
- Building parameter inputs
- Post comparison table
- Color-coded pass/fail results

## CLI Usage

### CLI

```bash
# Select city for climatic loads (required)
post-selector --city "Edmonton" --width 40 --height 14 --plies 4 --size 2x6

# List available cities
post-selector --list-cities

# Filter cities by name/region
post-selector --list-cities "Alberta"
post-selector --list-cities "Calgary"

# List provinces/regions
post-selector --list-regions

# List available post sizes
post-selector --list-posts

# Run validation tests
post-selector --validate
```

### Full Example

```bash
# 80x250x20 building in Grande Prairie, 4-ply 2x8 @ 4ft spacing
post-selector --city "Grande Prairie" \
    --width 80 --length 250 --height 20 \
    --spacing 4 --slope 4 \
    --plies 4 --size 2x8
```

### Python API

```python
from post_selector import run_calculation, load_cities_from_csv

# Load city database first
load_cities_from_csv()

# Calculate using city name
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
print(result.summary())
print(f"PASS" if result.capacity.is_ok else "FAIL")
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--city` | *required* | City name for NBCC climatic data |
| `--width` | 32 | Building width (ft) |
| `--length` | 40 | Building length (ft) |
| `--height` | 12 | Eave height (ft) |
| `--spacing` | 8 | Post spacing (ft) |
| `--slope` | 4 | Roof slope (x:12) |
| `--dead` | 10 | Dead load (psf) |
| `--plies` | 4 | Number of plies (3 or 4) |
| `--size` | 2x6 | Post size (2x6 or 2x8) |
| `--importance` | normal | low, normal, high, post_disaster |
| `--snow-exposure` | sheltered | sheltered, exposed, exposed_north |
| `--wind-exposure` | exposed | exposed, sheltered |

## Design Codes

- NBCC-2010 Division B, Sections 4.1.6 (Snow) and 4.1.7 (Wind)
- CSA O86-09, Engineering Design in Wood
- ASABE EP486.1, Shallow Post Foundation Design
- NDS AWC DA6 (post-frame bending model)

## Running Tests

```bash
pytest tests/
```