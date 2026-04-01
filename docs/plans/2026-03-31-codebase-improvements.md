# Post Selector Codebase Improvement Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix all bugs, architectural issues, and expand test coverage for the Post Selector structural engineering calculator.

**Architecture:** Refactor core.py to eliminate global mutable state, use proper Python packaging for data files, extract magic numbers into named constants, add input validation, and fix the critical dead_load default bug. Keep the same public API signatures.

**Tech Stack:** Python 3.9+, dataclasses, pytest, Streamlit (optional)

---

### Task 1: Fix Critical Bug + Dead Imports

**Files:**
- Modify: `post_selector/core.py`

**Step 1: Fix dead_load_psf default**

Change `run_calculation()` parameter default from 80 to 10 to match documented behavior:

```python
dead_load_psf=10,  # was 80, matches README default
```

**Step 2: Remove dead imports**

Remove `json` (line 19) and `sys` (line 20) — both unused. Remove the inner `import csv` (line 81) since it's already imported at top level (line 21). Remove the inner `import os` (line 74) and add `os` to top-level imports.

**Step 3: Run tests**

Run: `pytest tests/ -v`
Expected: All 3 tests pass

---

### Task 2: Extract Constants + Fix CSV Path Loading

**Files:**
- Modify: `post_selector/core.py`

**Step 1: Add named constants near top of file**

```python
FT_TO_M = 0.3048
IN_TO_MM = 25.4
PSF_TO_KPA = 20.9
GIRT_SPACING_IN = 24.0
DEFAULT_EMBED_DEPTH_FT = 4.0
K_SPLICE = 0.8
```

**Step 2: Replace magic numbers throughout**

- `0.3048` → `FT_TO_M` (BuildingParams properties)
- `25.4` → `IN_TO_MM` (girt spacing calculation)
- `24.0 * 25.4` → `GIRT_SPACING_IN * IN_TO_MM`
- `4.0 * 0.3048` → `DEFAULT_EMBED_DEPTH_FT * FT_TO_M`
- `0.8` (K_splice) → `K_SPLICE`

**Step 3: Fix CSV path loading**

Replace the fragile `os.path.dirname(__file__), "..", "data"` with `pathlib`:

```python
from pathlib import Path

def _default_csv_path() -> Path:
    return Path(__file__).resolve().parent.parent / "data" / "nbcc_c2_climatic_data.csv"
```

Update `load_cities_from_csv` to accept `Optional[Union[str, Path]]`.

**Step 4: Run tests**

Run: `pytest tests/ -v`
Expected: All tests pass

---

### Task 3: Refactor find_city — Remove Side Effects

**Files:**
- Modify: `post_selector/core.py`
- Modify: `post_selector/cli.py` (handle disambiguation at CLI level)

**Step 1: Add exception class**

```python
class CityNotFoundError(ValueError):
    pass

class AmbiguousCityError(ValueError):
    def __init__(self, name, matches):
        self.name = name
        self.matches = matches
        super().__init__(f"Multiple cities match '{name}': {', '.join(m[0] for m in matches)}")
```

**Step 2: Refactor find_city**

```python
def find_city(name: str) -> Optional[Tuple[str, float, float, float, float]]:
    city_db = get_city_db()
    name_lower = name.lower()
    matches = [c for c in city_db if name_lower in c[0].lower()]
    if len(matches) == 0:
        return None
    if len(matches) == 1:
        return matches[0]
    exact = [c for c in matches if c[0].lower().startswith(name_lower)]
    if len(exact) == 1:
        return exact[0]
    raise AmbiguousCityError(name, matches)
```

**Step 3: Update cli.py to catch AmbiguousCityError**

In `main()`, wrap the calculation call:

```python
try:
    result = run_calculation(...)
except AmbiguousCityError as e:
    print(f"Error: {e}")
    print("Please be more specific. Matching cities:")
    for m in e.matches:
        print(f"  {m[0]}")
    return 1
```

**Step 4: Update ClimaticLoads.from_nbcc_city**

```python
@classmethod
def from_nbcc_city(cls, city_name: str, importance: str = "normal"):
    try:
        city = find_city(city_name)
    except AmbiguousCityError:
        raise
    if city is None:
        raise CityNotFoundError(f"City '{city_name}' not found in NBCC database")
    ...
```

**Step 5: Run tests**

Run: `pytest tests/ -v`
Expected: All tests pass

---

### Task 4: Add Input Validation

**Files:**
- Modify: `post_selector/core.py`

**Step 1: Add `__post_init__` validation to BuildingParams**

```python
@dataclass
class BuildingParams:
    ...
    
    VALID_IMPORTANCE = ("low", "normal", "high", "post_disaster")
    
    def __post_init__(self):
        if self.width_ft <= 0:
            raise ValueError("width_ft must be positive")
        if self.length_ft <= 0:
            raise ValueError("length_ft must be positive")
        if self.eave_height_ft <= 0:
            raise ValueError("eave_height_ft must be positive")
        if self.post_spacing_ft <= 0:
            raise ValueError("post_spacing_ft must be positive")
        if self.roof_slope < 0:
            raise ValueError("roof_slope must be non-negative")
        if self.dead_load_psf < 0:
            raise ValueError("dead_load_psf must be non-negative")
        if self.importance not in self.VALID_IMPORTANCE:
            raise ValueError(f"importance must be one of {self.VALID_IMPORTANCE}")
```

**Step 2: Add validation to run_calculation**

```python
VALID_PLIES = (3, 4)
VALID_SIZES = ("2x6", "2x8")

def run_calculation(...) -> FullResult:
    if plies not in VALID_PLIES:
        raise ValueError(f"plies must be one of {VALID_PLIES}")
    if size not in VALID_SIZES:
        raise ValueError(f"size must be one of {VALID_SIZES}")
    ...
```

**Step 3: Run tests**

Run: `pytest tests/ -v`
Expected: All tests pass

---

### Task 5: Fix CLI Return Types + Add --version

**Files:**
- Modify: `post_selector/cli.py`
- Modify: `post_selector/__init__.py`

**Step 1: Fix main() to always return int**

```python
def main():
    ...
    if args.validate:
        run_validation()
        return 0  # was: return run_validation() which returns bool
    
    if args.list_posts:
        ...
        return 0  # was: return 0 (already correct)
    
    ...
    return 0 if result.capacity.is_ok else 1
```

**Step 2: Add --version flag**

```python
from . import __version__

parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
```

**Step 3: Run tests**

Run: `pytest tests/ -v`

---

### Task 6: Fix Streamlit App

**Files:**
- Modify: `post_selector/app.py`

**Step 1: Remove sys.path hack**

Remove the `sys.path.insert(0, ...)` block. The package should be properly installed via `pip install -e .`.

**Step 2: Add error handling for calculations**

Wrap `run_calculation` call in try/except, show user-friendly error with `st.error()`.

**Step 3: Fix "Compare All Posts" with proper binary search**

Replace the linear scan with binary search:

```python
def find_max_spacing(city, width, length, height, slope, dead_load, plies, size, importance, snow_exp, wind_exp):
    lo, hi = 2.0, 12.0
    best = 0
    for _ in range(20):  # ~0.01ft precision
        mid = (lo + hi) / 2
        try:
            r = run_calculation(city_name=city, ..., post_spacing_ft=mid, plies=plies, size=size, ...)
            if r.capacity.is_ok:
                best = mid
                lo = mid
            else:
                hi = mid
        except Exception:
            hi = mid
    return best
```

**Step 4: Increase city list limit and show count**

Change `city_names[:20]` to show more results with a note about filtering.

---

### Task 7: Expand Test Coverage

**Files:**
- Modify: `tests/test_post.py`
- Create: `tests/test_snow.py`
- Create: `tests/test_wind.py`
- Create: `tests/test_city.py`
- Create: `tests/conftest.py`

**Step 1: Create conftest.py with shared fixtures**

```python
import pytest
from post_selector import ClimaticLoads, BuildingParams

@pytest.fixture
def edmonton_climate():
    return ClimaticLoads(Ss=1.76, Sr=0.1, q=0.43, source="test")

@pytest.fixture
def typical_building():
    return BuildingParams(
        width_ft=80, length_ft=250, eave_height_ft=20,
        post_spacing_ft=4, roof_slope=4, dead_load_psf=10
    )

@pytest.fixture
def heavy_climate():
    return ClimaticLoads(Ss=27.88 / 20.9, Sr=0.0, q=0.5, source="test")
```

**Step 2: Add snow load tests**

Test cases:
- Flat roof (slope=0) should have Cs=1.0
- Steep roof (slope>=60 for slippery) should have Cs=0.0
- Sheltered vs exposed should give different Cw
- Balanced vs unbalanced design load selection

**Step 3: Add wind load tests**

Test cases:
- Exposed vs sheltered Ce calculation
- Known Ce value at reference height
- Wall and roof pressures are positive

**Step 4: Add city search tests**

Test cases:
- Exact match returns correct city
- Partial match works
- Non-existent city returns None
- Ambiguous match raises AmbiguousCityError

**Step 5: Add capacity validation tests**

Test cases:
- run_validation() values match spreadsheet (parametrized)
- Edge case: minimum building size
- Post size validation rejects invalid sizes

**Step 6: Add input validation tests**

Test cases:
- Negative width raises ValueError
- Invalid importance raises ValueError
- Invalid plies raises ValueError

**Step 7: Run all tests**

Run: `pytest tests/ -v`
Expected: All tests pass

---

### Task 8: Final Verification

**Step 1: Run full test suite**

Run: `pytest tests/ -v --tb=short`

**Step 2: Run validation check**

Run: `python -m post_selector.core` (runs run_validation)

**Step 3: Verify CLI works**

Run: `python -m post_selector.cli --version`
Run: `python -m post_selector.cli --list-regions`
Run: `python -m post_selector.cli --city "Edmonton" --width 80 --height 20 --plies 4 --size 2x8`

**Step 4: Verify existing tests still pass**

Run: `pytest tests/ -v`
