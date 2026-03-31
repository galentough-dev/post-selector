#!/usr/bin/env python3
"""
Post Selector - Laminated Timber Post Capacity Calculator
=========================================================
Replicates the engineering calculations from "Post Selector 2023.xlsx"
by Hillier Manufacturing Inc.

Design codes: NBCC-2010, CSA O86-09, ASCE 7-05 (US option)
Methodology: Limit States Design (similar to LRFD per NDS-2005)

References:
  - NBCC-2010 Division B, Sections 4.1.6 (Snow) and 4.1.7 (Wind)
  - CSA O86-09, Engineering Design in Wood
  - ASABE EP486.1, Shallow Post Foundation Design
  - NDS AWC DA6 (post-frame bending model)
"""

import math
import json
import sys
import csv
from dataclasses import dataclass, field
from typing import Optional, Tuple

PSF_TO_KPA = 20.9

_CITY_DB = []


def get_city_db():
    """Return the loaded city database. Loads automatically if not loaded."""
    if not _CITY_DB:
        load_cities_from_csv()
    return _CITY_DB


@dataclass
class ClimaticLoads:
    """Site-specific climatic design loads."""

    Ss: float
    Sr: float
    q: float
    source: str = "manual"

    @classmethod
    def from_nbcc_city(cls, city_name: str, importance: str = "normal"):
        city = find_city(city_name)
        if city is None:
            raise ValueError(f"City '{city_name}' not found in NBCC database")
        label, Ss, Sr, q10, q50 = city
        q = q50 if importance in ("normal", "high", "post_disaster") else q10
        return cls(Ss=Ss, Sr=Sr, q=q, source=f"NBCC-2010 ({label})")

    @classmethod
    def from_us_values(cls, pg_psf: float, V_mph: float):
        Ss = pg_psf / PSF_TO_KPA
        Sr = 0.0
        q = 0.00064645 * (V_mph / 2.236936292054 / 1.52) ** 2
        return cls(Ss=Ss, Sr=Sr, q=q, source="US (ASCE 7-05)")


def load_cities_from_csv(filepath: Optional[str] = None):
    """Load full NBCC C-2 city database from CSV file.
    Expected columns: label, Ss, Sr, q10, q50

    Args:
        filepath: Path to CSV file. Defaults to data/nbcc_c2_climatic_data.csv in package.
    """
    global _CITY_DB
    _CITY_DB = []

    if filepath is None:
        import os

        filepath = os.path.join(
            os.path.dirname(__file__), "..", "data", "nbcc_c2_climatic_data.csv"
        )

    try:
        import csv

        with open(filepath, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    _CITY_DB.append(
                        (
                            row["label"],
                            float(row["Ss"]),
                            float(row["Sr"]),
                            float(row["q10"]),
                            float(row["q50"]),
                        )
                    )
                except (ValueError, KeyError):
                    continue
    except FileNotFoundError:
        raise FileNotFoundError(f"Climatic data file not found: {filepath}")


def find_city(name: str) -> Optional[Tuple[str, float, float, float, float]]:
    """Find a city in the database by partial name match (case-insensitive)."""
    if not _CITY_DB:
        raise RuntimeError(
            "City database not loaded. Call load_cities_from_csv() first."
        )
    name_lower = name.lower()
    matches = [c for c in _CITY_DB if name_lower in c[0].lower()]
    if len(matches) == 1:
        return matches[0]
    elif len(matches) > 1:
        exact = [c for c in matches if c[0].lower().startswith(name_lower)]
        if len(exact) == 1:
            return exact[0]
        print(f"Multiple matches found for '{name}':")
        for i, m in enumerate(matches):
            print(f"  {i + 1}. {m[0]}")
        return matches[0]
    return None


# =============================================================================
# Post Properties Database
# =============================================================================


@dataclass
class PostProperties:
    """Laminated timber post section properties (Hillier Mfg.)"""

    species_grade: str
    plies: int
    size: str
    Mr: float  # Factored moment resistance (kN-m) - from testing
    A: float  # Cross-sectional area (mm²)
    fc: float  # Specified compressive strength parallel to grain (MPa)
    E05: float  # 5th-percentile modulus of elasticity (MPa)
    d: float  # Depth of member (mm)


POST_DATABASE = [
    PostProperties("SPF No.1/2 PWF", 3, "2x6", 5.49, 15960, 11.5, 6500, 140),
    PostProperties("SPF No.1/2 PWF", 3, "2x8", 6.33, 20976, 11.5, 6500, 184),
    PostProperties("SPF No.1/2 PWF", 4, "2x6", 6.86, 21280, 11.5, 6500, 140),
    PostProperties("SPF No.1/2 PWF", 4, "2x8", 10.46, 27968, 11.5, 6500, 184),
]


def get_post(plies: int, size: str) -> PostProperties:
    """Look up a post from the database."""
    for p in POST_DATABASE:
        if p.plies == plies and p.size == size:
            return p
    raise ValueError(f"Post not found: {plies}-ply {size}")


# =============================================================================
# Input Data Classes
# =============================================================================


@dataclass
class BuildingParams:
    """Building geometry and use parameters."""

    width_ft: float
    length_ft: float
    eave_height_ft: float
    post_spacing_ft: float
    roof_slope: float
    dead_load_psf: float
    importance: str = "normal"

    @property
    def importance_factor(self) -> float:
        factors = {"low": 0.8, "normal": 1.0, "high": 1.15, "post_disaster": 1.25}
        return factors[self.importance]

    @property
    def width_m(self) -> float:
        return self.width_ft * 0.3048

    @property
    def length_m(self) -> float:
        return self.length_ft * 0.3048

    @property
    def eave_height_m(self) -> float:
        return self.eave_height_ft * 0.3048

    @property
    def post_spacing_m(self) -> float:
        return self.post_spacing_ft * 0.3048

    @property
    def slope_degrees(self) -> float:
        return math.degrees(math.atan(self.roof_slope / 12.0))

    @property
    def roof_height_ft(self) -> float:
        return self.eave_height_ft + (self.roof_slope / 12.0) * (self.width_ft / 2.0)

    @property
    def reference_height_ft(self) -> float:
        return (self.eave_height_ft + self.roof_height_ft) / 2.0

    @property
    def reference_height_m(self) -> float:
        return self.reference_height_ft * 0.3048

    @property
    def dead_load_kPa(self) -> float:
        return self.dead_load_psf / PSF_TO_KPA


# =============================================================================
# Snow Load Calculations (NBCC-2010 Division B 4.1.6.2)
# =============================================================================


@dataclass
class SnowLoadResult:
    Cb: float
    Cw: float
    Cs: float
    Ca_balanced: float
    Ca_unbalanced: float
    S_balanced: float
    S_unbalanced: float
    S_design: float


def calculate_snow_load(
    climate: ClimaticLoads,
    building: BuildingParams,
    exposure: str = "sheltered",
    roof_type: str = "unobstructed_slippery",
) -> SnowLoadResult:
    Is = building.importance_factor
    Ss = climate.Ss
    Sr = climate.Sr
    alpha = building.slope_degrees

    Cb = 0.8

    Cw_values = {"sheltered": 1.0, "exposed": 0.75, "exposed_north": 0.5}
    Cw = Cw_values.get(exposure, 1.0)

    if roof_type == "unobstructed_slippery":
        if alpha <= 15:
            Cs = 1.0
        elif alpha >= 60:
            Cs = 0.0
        else:
            Cs = (60 - alpha) / 45.0
    else:
        if alpha <= 30:
            Cs = 1.0
        elif alpha >= 70:
            Cs = 0.0
        else:
            Cs = (70 - alpha) / 40.0

    Ca_balanced = 1.0

    if alpha < 15:
        Ca_unbalanced = 0.0
    elif alpha > 20:
        Ca_unbalanced = 1.25
    else:
        Ca_unbalanced = 0.25 + alpha / 20.0

    S_balanced = Is * (Ss * Cb * Cw * Cs * Ca_balanced + Sr)
    if Ca_unbalanced > 0:
        S_unbalanced = Is * (Ss * Cb * Cw * Cs * Ca_unbalanced + Sr)
    else:
        S_unbalanced = 0.0

    S_design = max(S_balanced, S_unbalanced)

    return SnowLoadResult(
        Cb=Cb,
        Cw=Cw,
        Cs=Cs,
        Ca_balanced=Ca_balanced,
        Ca_unbalanced=Ca_unbalanced,
        S_balanced=S_balanced,
        S_unbalanced=S_unbalanced,
        S_design=S_design,
    )


# =============================================================================
# Wind Load Calculations (NBCC-2010 Division B 4.1.7.1)
# =============================================================================


@dataclass
class WindLoadResult:
    Ce: float
    Cpi_min: float
    Cpi_max: float
    Cgi: float
    Iw: float
    q: float
    wall_wind_load: float
    roof_wind_load: float
    wall_wind_psf: float
    roof_wind_psf: float


def _interpolate_CpCg(alpha: float, table_values: list) -> float:
    if alpha <= table_values[0][0]:
        return table_values[0][1]
    if alpha >= table_values[-1][0]:
        return table_values[-1][1]
    for i in range(len(table_values) - 1):
        a1, v1 = table_values[i]
        a2, v2 = table_values[i + 1]
        if a1 <= alpha <= a2:
            return v1 + (v2 - v1) * (alpha - a1) / (a2 - a1)
    return table_values[-1][1]


def calculate_wind_load(
    climate: ClimaticLoads,
    building: BuildingParams,
    cpi_category: int = 2,
    exposure: str = "exposed",
) -> WindLoadResult:
    Iw = building.importance_factor
    q = climate.q
    h_m = building.reference_height_m
    alpha = building.slope_degrees

    if exposure == "exposed":
        Ce = max((h_m / 10.0) ** 0.2, 0.9)
    else:
        Ce = max(0.7 * (h_m / 12.0) ** 0.3, 0.7)

    Cpi_table = {1: (-0.15, 0.0), 2: (-0.45, 0.3), 3: (-0.7, 0.7)}
    Cpi_min, Cpi_max = Cpi_table[cpi_category]

    Cgi = 2.0

    pi_min = Iw * q * Ce * Cpi_min * Cgi
    pi_max = Iw * q * Ce * Cpi_max * Cgi

    base = Iw * q * Ce

    # External CpCg coefficients from NBCC-2010 Figure I-7
    CpCg_1_A = _interpolate_CpCg(alpha, [(5, 0.75), (20, 1.0), (30, 1.05), (90, 1.05)])
    CpCg_2_A = _interpolate_CpCg(alpha, [(5, -1.3), (20, -1.3), (30, 0.4), (90, 1.05)])
    CpCg_3_A = _interpolate_CpCg(alpha, [(5, -0.7), (20, -0.9), (30, -0.8), (90, -0.7)])
    CpCg_4_A = _interpolate_CpCg(
        alpha, [(5, -0.55), (20, -0.8), (30, -0.7), (90, -0.7)]
    )

    pe_A = {
        1: base * CpCg_1_A,
        2: base * CpCg_2_A,
        3: base * CpCg_3_A,
        4: base * CpCg_4_A,
    }

    CpCg_5_B = 0.75
    CpCg_6_B = -0.55
    pe_B = {
        1: base * (-0.85),
        2: base * (-1.3),
        3: base * (-0.7),
        4: base * (-0.85),
        5: base * CpCg_5_B,
        6: base * CpCg_6_B,
    }

    p_all = {}
    for s in [1, 2, 3, 4]:
        p_all.setdefault(s, [])
        p_all[s].append(pe_A[s] - pi_min)
        p_all[s].append(pe_A[s] - pi_max)
    for s in [1, 2, 3, 4, 5, 6]:
        p_all.setdefault(s, [])
        p_all[s].append(pe_B[s] - pi_min)
        p_all[s].append(pe_B[s] - pi_max)

    wall_pressures_1 = p_all[1]
    wall_pressures_4 = p_all[4]
    wall_max = max(
        max(abs(min(wall_pressures_1)), abs(max(wall_pressures_1))),
        max(abs(min(wall_pressures_4)), abs(max(wall_pressures_4))),
    )

    roof_pressures_2 = p_all[2]
    roof_pressures_3 = p_all[3]
    roof_max_2 = max(0, max(roof_pressures_2))
    roof_max_3 = max(0, max(roof_pressures_3))
    roof_load = max(roof_max_2, roof_max_3) * math.cos(math.radians(alpha))

    return WindLoadResult(
        Ce=Ce,
        Cpi_min=Cpi_min,
        Cpi_max=Cpi_max,
        Cgi=Cgi,
        Iw=Iw,
        q=q,
        wall_wind_load=wall_max,
        roof_wind_load=roof_load,
        wall_wind_psf=wall_max * PSF_TO_KPA,
        roof_wind_psf=roof_load * PSF_TO_KPA,
    )


# =============================================================================
# Structural Analysis - Post Loading
# =============================================================================


@dataclass
class LoadingResult:
    DL_kN: float
    SL_kN: float
    WLr_kN: float
    WLw_kN_per_m: float
    Pf_LC3: float
    Pf_LC5: float
    Mf_LC5: float
    Mmax_base: float
    Mx1: float
    K_splice: float


def calculate_loading(
    building: BuildingParams,
    snow: SnowLoadResult,
    wind: WindLoadResult,
    override_snow_psf: Optional[float] = None,
    override_wind_psf: Optional[float] = None,
) -> LoadingResult:
    W_m = building.width_m
    sp_m = building.post_spacing_m
    H_m = building.eave_height_m

    DL_kPa = building.dead_load_kPa
    DL_kN = DL_kPa * W_m * sp_m / 2.0

    if override_snow_psf and override_snow_psf > 0:
        S_kPa = override_snow_psf / PSF_TO_KPA
    else:
        S_kPa = snow.S_design
    SL_kN = S_kPa * W_m * sp_m / 2.0

    WLr_kPa = wind.roof_wind_load
    WLr_kN = WLr_kPa * W_m * sp_m / 2.0

    if override_wind_psf and override_wind_psf > 0:
        WLw_kPa = override_wind_psf / PSF_TO_KPA
    else:
        WLw_kPa = wind.wall_wind_load
    WLw_kN_per_m = WLw_kPa * sp_m

    wf = 1.4 * WLw_kN_per_m

    R1 = 3.0 / 8.0 * wf * H_m
    Mmax_base = 1.0 / 8.0 * wf * H_m**2
    Mx1 = 9.0 / 128.0 * wf * H_m**2

    D_embed = 4.0 * 0.3048
    x3 = D_embed
    Mx3 = R1 * (H_m - x3) - wf * (H_m - x3) ** 2 / 2.0
    Mx4 = R1 * H_m - wf * H_m**2 / 2.0

    K_splice = 0.8
    Mf = K_splice * max(abs(Mmax_base), abs(Mx1), abs(Mx3), abs(Mx4))

    Pf_LC3 = 1.25 * DL_kN + 1.5 * SL_kN + 0.4 * WLr_kN
    Pf_LC5 = 1.25 * DL_kN + 1.4 * WLr_kN + 0.5 * SL_kN

    return LoadingResult(
        DL_kN=DL_kN,
        SL_kN=SL_kN,
        WLr_kN=WLr_kN,
        WLw_kN_per_m=WLw_kN_per_m,
        Pf_LC3=Pf_LC3,
        Pf_LC5=Pf_LC5,
        Mf_LC5=Mf,
        Mmax_base=Mmax_base,
        Mx1=Mx1,
        K_splice=K_splice,
    )


# =============================================================================
# Post Capacity Calculation (CSA O86-09)
# =============================================================================


@dataclass
class CapacityResult:
    Fc: float
    KZc: float
    Kc: float
    Cc_d: float
    Cc_b: float
    Pr: float
    Mr: float
    ratio_LC3: float
    ratio_LC5: float
    pass_LC3: bool
    pass_LC5: bool

    @property
    def is_ok(self) -> bool:
        return self.pass_LC3 and self.pass_LC5


def calculate_capacity(
    post: PostProperties, building: BuildingParams, loading: LoadingResult
) -> CapacityResult:
    H_m = building.eave_height_m

    alpha_buildup = 1.0
    phi = 0.8
    KD = 1.0
    KD_wind = 1.15
    KH = 1.0
    KSc = 1.0
    KT = 0.85
    KSE = 1.0
    Ke = 0.8
    K_adhesive = 1.1

    fc = post.fc
    E05 = post.E05
    A = post.A
    d = post.d

    Fc = fc * KD * KH * KSc * KT

    girt_spacing_mm = 24.0 * 25.4

    Ld = 11.0 / 10.0 * H_m * 1000.0
    Lb = girt_spacing_mm

    Cc_d = Ke * Ld / d
    Cc_b = Ke * Lb / (38.0 * post.plies)
    Cc = max(Cc_d, Cc_b)

    KZc_d = min(1.3, 6.3 * (d * Ld) ** (-0.13))
    KZc_b = min(1.3, 6.3 * (38.0 * post.plies * Lb) ** (-0.13))
    KZc = min(KZc_d, KZc_b)

    Kc = (1.0 + Fc * KZc * Cc**3 / (35.0 * E05 * KSE * KT)) ** (-1)

    Pr = alpha_buildup * phi * Fc * A * KZc * Kc * K_adhesive / 1000.0

    Mr = post.Mr * KD_wind

    ratio_LC3 = loading.Pf_LC3 / Pr
    ratio_LC5 = loading.Pf_LC5 / Pr + loading.Mf_LC5 / Mr

    return CapacityResult(
        Fc=Fc,
        KZc=KZc,
        Kc=Kc,
        Cc_d=Cc_d,
        Cc_b=Cc_b,
        Pr=Pr,
        Mr=Mr,
        ratio_LC3=ratio_LC3,
        ratio_LC5=ratio_LC5,
        pass_LC3=ratio_LC3 < 1.0,
        pass_LC5=ratio_LC5 < 1.0,
    )


# =============================================================================
# Main Calculation Engine
# =============================================================================


@dataclass
class FullResult:
    climate: ClimaticLoads
    building: BuildingParams
    post: PostProperties
    snow: SnowLoadResult
    wind: WindLoadResult
    loading: LoadingResult
    capacity: CapacityResult

    def summary(self) -> str:
        lines = []
        lines.append("=" * 72)
        lines.append("POST SELECTOR - Laminated Timber Post Capacity Check")
        lines.append("Hillier Manufacturing Inc.")
        lines.append("Design Codes: NBCC-2010, CSA O86-09")
        lines.append("=" * 72)

        lines.append(f"\n--- Climatic Data ({self.climate.source}) ---")
        lines.append(f"  Ground snow load, Ss        = {self.climate.Ss:.1f} kPa")
        lines.append(f"  Associated rain load, Sr    = {self.climate.Sr:.1f} kPa")
        lines.append(f"  Wind velocity pressure, q   = {self.climate.q:.2f} kPa")

        lines.append(f"\n--- Building Parameters ---")
        lines.append(
            f"  Width  W = {self.building.width_ft:.0f} ft ({self.building.width_m:.2f} m)"
        )
        lines.append(
            f"  Length L = {self.building.length_ft:.0f} ft ({self.building.length_m:.2f} m)"
        )
        lines.append(
            f"  Eave   H = {self.building.eave_height_ft:.0f} ft ({self.building.eave_height_m:.2f} m)"
        )
        lines.append(
            f"  Slope     = {self.building.roof_slope:.0f}:12 ({self.building.slope_degrees:.1f} deg)"
        )
        lines.append(
            f"  Spacing  = {self.building.post_spacing_ft:.0f} ft ({self.building.post_spacing_m:.2f} m)"
        )
        lines.append(
            f"  Dead ld  = {self.building.dead_load_psf:.0f} psf ({self.building.dead_load_kPa:.2f} kPa)"
        )
        lines.append(
            f"  Importance = {self.building.importance_factor:.1f} ({self.building.importance})"
        )

        lines.append(f"\n--- Snow Load (NBCC-2010 4.1.6.2) ---")
        lines.append(
            f"  Cb={self.snow.Cb:.1f}  Cw={self.snow.Cw:.2f}  Cs={self.snow.Cs:.4f}"
        )
        lines.append(
            f"  Balanced   S = {self.snow.S_balanced:.3f} kPa ({self.snow.S_balanced * PSF_TO_KPA:.1f} psf)"
        )
        lines.append(
            f"  Unbalanced S = {self.snow.S_unbalanced:.3f} kPa ({self.snow.S_unbalanced * PSF_TO_KPA:.1f} psf)"
        )
        lines.append(
            f"  Design     S = {self.snow.S_design:.3f} kPa ({self.snow.S_design * PSF_TO_KPA:.1f} psf)"
        )

        lines.append(f"\n--- Wind Load (NBCC-2010 4.1.7.1) ---")
        lines.append(f"  Ce = {self.wind.Ce:.2f}")
        lines.append(
            f"  Wall wind = {self.wind.wall_wind_load:.4f} kPa ({self.wind.wall_wind_psf:.1f} psf)"
        )
        lines.append(
            f"  Roof wind = {self.wind.roof_wind_load:.4f} kPa ({self.wind.roof_wind_psf:.1f} psf)"
        )

        lines.append(
            f"\n--- Post: {self.post.plies}-ply {self.post.size} {self.post.species_grade} ---"
        )
        lines.append(f"  A={self.post.A} mm²  d={self.post.d} mm")

        lines.append(f"\n--- Factored Loads ---")
        lines.append(f"  LC3 Pf = {self.loading.Pf_LC3:.2f} kN")
        lines.append(
            f"  LC5 Pf = {self.loading.Pf_LC5:.2f} kN  Mf = {self.loading.Mf_LC5:.3f} kN-m"
        )

        lines.append(f"\n--- Capacity ---")
        lines.append(
            f"  Pr = {self.capacity.Pr:.3f} kN   Mr = {self.capacity.Mr:.3f} kN-m"
        )
        lines.append(f"  Kc = {self.capacity.Kc:.4f}  KZc = {self.capacity.KZc:.4f}")

        lines.append(f"\n--- Code Checks ---")
        s3 = "OK" if self.capacity.pass_LC3 else "FAILS"
        s5 = "OK" if self.capacity.pass_LC5 else "FAILS"
        lines.append(f"  LC3  Pf/Pr         = {self.capacity.ratio_LC3:.4f}  [{s3}]")
        lines.append(f"  LC5  Pf/Pr + Mf/Mr = {self.capacity.ratio_LC5:.4f}  [{s5}]")

        ok = "POST IS OK" if self.capacity.is_ok else "POST IS INADEQUATE"
        lines.append(f"\n  >>> {ok} <<<")
        return "\n".join(lines)


def run_calculation(
    city_name=None,
    manual_loads=None,
    us_snow_psf=None,
    us_wind_mph=None,
    width_ft=32,
    length_ft=40,
    eave_height_ft=12,
    post_spacing_ft=8,
    roof_slope=4,
    dead_load_psf=80,
    importance="normal",
    plies=4,
    size="2x6",
    snow_exposure="sheltered",
    snow_roof_type="unobstructed_slippery",
    wind_cpi_category=2,
    wind_exposure="exposed",
    override_snow_psf=None,
    override_wind_psf=None,
) -> FullResult:
    if city_name:
        climate = ClimaticLoads.from_nbcc_city(city_name, importance)
    elif us_snow_psf is not None and us_wind_mph is not None:
        climate = ClimaticLoads.from_us_values(us_snow_psf, us_wind_mph)
    elif manual_loads:
        climate = manual_loads
    else:
        raise ValueError("Must provide city_name, manual_loads, or US values")

    building = BuildingParams(
        width_ft=width_ft,
        length_ft=length_ft,
        eave_height_ft=eave_height_ft,
        post_spacing_ft=post_spacing_ft,
        roof_slope=roof_slope,
        dead_load_psf=dead_load_psf,
        importance=importance,
    )

    post = get_post(plies, size)
    snow = calculate_snow_load(climate, building, snow_exposure, snow_roof_type)
    wind = calculate_wind_load(climate, building, wind_cpi_category, wind_exposure)
    loading = calculate_loading(
        building, snow, wind, override_snow_psf, override_wind_psf
    )
    capacity = calculate_capacity(post, building, loading)

    return FullResult(
        climate=climate,
        building=building,
        post=post,
        snow=snow,
        wind=wind,
        loading=loading,
        capacity=capacity,
    )


# =============================================================================
# CLI Entry Point
# =============================================================================


def run_validation():
    """Run validation tests against known spreadsheet values."""
    load_cities_from_csv()
    print("Running validation: Grande Prairie, AB — 4-ply 2x6...\n")
    result = run_calculation(
        city_name="Grande Prairie",
        width_ft=32,
        length_ft=40,
        eave_height_ft=12,
        post_spacing_ft=8,
        roof_slope=4,
        dead_load_psf=80,
        importance="normal",
        plies=4,
        size="2x6",
    )
    print(result.summary())

    print("\n\n--- VALIDATION vs SPREADSHEET ---")
    checks = [
        ("Snow S_design", result.snow.S_design, 2.00486, "kPa"),
        ("Wall wind", result.wind.wall_wind_load, 0.72521, "kPa"),
        ("Roof wind", result.wind.roof_wind_load, 0.07343, "kPa"),
        ("Pf LC3", result.loading.Pf_LC3, 93.008, "kN"),
        ("Pf LC5", result.loading.Pf_LC5, 70.040, "kN"),
        ("Mf LC5", result.loading.Mf_LC5, 3.312, "kN-m"),
        ("Pr", result.capacity.Pr, 121.875, "kN"),
        ("Mr", result.capacity.Mr, 7.889, "kN-m"),
        ("LC3 ratio", result.capacity.ratio_LC3, 0.7631, ""),
        ("LC5 ratio", result.capacity.ratio_LC5, 0.9945, ""),
    ]
    ok = True
    for name, calc, exp, unit in checks:
        pct = abs(calc - exp) / abs(exp) * 100 if exp else 0
        s = "✓" if pct < 0.5 else "✗"
        if pct >= 0.5:
            ok = False
        print(f"  {s} {name:20s}: {calc:12.6f} vs {exp:12.6f}  ({pct:.3f}%) {unit}")
    print(f"\n  {'ALL CHECKS PASSED ✓' if ok else 'SOME CHECKS FAILED ✗'}")
    return ok


def main():
    run_validation()


if __name__ == "__main__":
    main()
