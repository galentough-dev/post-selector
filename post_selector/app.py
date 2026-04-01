"""Streamlit frontend for Post Selector."""

import streamlit as st
from post_selector import (
    run_calculation,
    load_cities_from_csv,
    get_city_db,
    POST_DATABASE,
    PSF_TO_KPA,
    CityNotFoundError,
    AmbiguousCityError,
)

st.set_page_config(
    page_title="Post Selector",
    page_icon="🏗️",
    layout="wide",
)

st.markdown(
    """
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .result-pass {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #c3e6cb;
    }
    .result-fail {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #f5c6cb;
    }
    .metric-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #dee2e6;
    }
    .stMetric > div {
        background-color: #f8f9fa;
        padding: 0.5rem 1rem;
        border-radius: 0.5rem;
    }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_resource
def load_db():
    load_cities_from_csv()
    return get_city_db()


cities = load_db()

st.markdown('<p class="main-header">Post Selector</p>', unsafe_allow_html=True)
st.markdown(
    '<p class="sub-header">Laminated Timber Post Capacity Calculator - NBCC-2010, CSA O86-09</p>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Location")

    city_names = [c[0] for c in cities]
    city_search = st.text_input("Search city", placeholder="Type to search...")

    if city_search:
        filtered = [c for c in city_names if city_search.lower() in c.lower()]
    else:
        filtered = city_names[:50]

    if not filtered:
        st.warning("No cities found. Try a different search.")
        selected_city = None
    else:
        selected_city = st.selectbox("Select city", filtered)

    city_data = None
    if selected_city:
        city_data = next((c for c in cities if c[0] == selected_city), None)

    if city_data:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Ss", f"{city_data[1]:.2f} kPa")
        with col2:
            st.metric("Sr", f"{city_data[2]:.2f} kPa")
        with col3:
            st.metric("q", f"{city_data[4]:.2f} kPa")

    st.divider()

    st.header("Building Parameters")

    col1, col2 = st.columns(2)
    with col1:
        width = st.number_input("Width (ft)", value=80, min_value=10, max_value=200)
        height = st.number_input(
            "Eave Height (ft)", value=20, min_value=8, max_value=40
        )
    with col2:
        length = st.number_input("Length (ft)", value=250, min_value=10, max_value=500)
        spacing = st.number_input(
            "Post Spacing (ft)", value=4.0, min_value=2.0, max_value=12.0, step=0.5
        )

    slope = st.number_input(
        "Roof Slope (x:12)",
        value=4.0,
        min_value=0.0,
        max_value=12.0,
        step=0.25,
        format="%.2f",
    )
    dead_load = st.number_input("Dead Load (psf)", value=80, min_value=5, max_value=200)

    st.divider()

    st.header("Post Selection")

    col1, col2 = st.columns(2)
    with col1:
        plies = st.radio("Plies", [3, 4], horizontal=True)
    with col2:
        size = st.radio("Size", ["2x6", "2x8"], horizontal=True)

    st.divider()

    st.header("Building Type")

    building_type = st.selectbox(
        "Building Use",
        [
            "Agricultural (barn, equipment storage)",
            "Residential (garage, shop)",
            "Commercial (warehouse, retail)",
            "Industrial (manufacturing)",
            "Community (school, arena)",
            "Post-disaster (fire hall, emergency)",
        ],
    )

    type_to_importance = {
        "Agricultural (barn, equipment storage)": "low",
        "Residential (garage, shop)": "normal",
        "Commercial (warehouse, retail)": "normal",
        "Industrial (manufacturing)": "normal",
        "Community (school, arena)": "high",
        "Post-disaster (fire hall, emergency)": "post_disaster",
    }

    importance = type_to_importance.get(building_type, "normal")

    importance_factors = {
        "low": 0.8,
        "normal": 1.0,
        "high": 1.15,
        "post_disaster": 1.25,
    }
    st.info(
        f"Importance Factor: {importance_factors.get(importance, 1.0)} ({importance})"
    )

    st.divider()

    st.header("Exposure")
    snow_exposure = st.selectbox(
        "Snow Exposure", ["sheltered", "exposed", "exposed_north"]
    )
    wind_exposure = st.selectbox("Wind Exposure", ["exposed", "sheltered"])

col_left, col_right = st.columns([2, 1])

with col_left:
    if st.button("Calculate", type="primary", use_container_width=True):
        if not selected_city:
            st.error("Please select a city first.")
        else:
            try:
                result = run_calculation(
                    city_name=selected_city,
                    width_ft=width,
                    length_ft=length,
                    eave_height_ft=height,
                    post_spacing_ft=spacing,
                    roof_slope=slope,
                    dead_load_psf=dead_load,
                    plies=plies,
                    size=size,
                    importance=importance,
                    snow_exposure=snow_exposure,
                    wind_exposure=wind_exposure,
                )

                st.session_state["result"] = result
                st.session_state["calculated"] = True

                if result.capacity.is_ok:
                    st.markdown(
                        '<div class="result-pass"><h2>PASS - POST IS OK</h2></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<div class="result-fail"><h2>FAIL - POST IS INADEQUATE</h2></div>',
                        unsafe_allow_html=True,
                    )

                st.subheader("Code Checks")
                col1, col2 = st.columns(2)
                with col1:
                    lc3_status = "OK" if result.capacity.pass_LC3 else "FAIL"
                    st.metric("LC3", f"{result.capacity.ratio_LC3:.4f}", lc3_status)
                with col2:
                    lc5_status = "OK" if result.capacity.pass_LC5 else "FAIL"
                    st.metric("LC5", f"{result.capacity.ratio_LC5:.4f}", lc5_status)

                st.subheader("Factored Loads")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Pf (LC3)", f"{result.loading.Pf_LC3:.2f} kN")
                with col2:
                    st.metric("Pf (LC5)", f"{result.loading.Pf_LC5:.2f} kN")
                with col3:
                    st.metric("Mf (LC5)", f"{result.loading.Mf_LC5:.3f} kN-m")

                st.subheader("Post Capacity")
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Pr", f"{result.capacity.Pr:.3f} kN")
                with col2:
                    st.metric("Mr", f"{result.capacity.Mr:.3f} kN-m")

                with st.expander("Climatic Data"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Snow Load**")
                        st.write(
                            f"Design: {result.snow.S_design:.3f} kPa ({result.snow.S_design * PSF_TO_KPA:.1f} psf)"
                        )
                    with col2:
                        st.write("**Wind Load**")
                        st.write(
                            f"Wall: {result.wind.wall_wind_load:.4f} kPa ({result.wind.wall_wind_psf:.1f} psf)"
                        )
                        st.write(
                            f"Roof: {result.wind.roof_wind_load:.4f} kPa ({result.wind.roof_wind_psf:.1f} psf)"
                        )

            except (CityNotFoundError, AmbiguousCityError) as e:
                st.error(f"City error: {e}")
            except ValueError as e:
                st.error(f"Input error: {e}")

with col_right:
    st.subheader("Compare Posts")

    if st.button("Compare All Posts", use_container_width=True):
        if not selected_city:
            st.error("Please select a city first.")
        else:
            st.write("Finding max spacing for each post...")

            results = []
            for post in POST_DATABASE:
                lo, hi = 2.0, 12.0
                best = 0.0
                for _ in range(20):
                    mid = (lo + hi) / 2.0
                    try:
                        r = run_calculation(
                            city_name=selected_city,
                            width_ft=width,
                            length_ft=length,
                            eave_height_ft=height,
                            post_spacing_ft=mid,
                            roof_slope=slope,
                            dead_load_psf=dead_load,
                            plies=post.plies,
                            size=post.size,
                            importance=importance,
                            snow_exposure=snow_exposure,
                            wind_exposure=wind_exposure,
                        )
                        if r.capacity.is_ok:
                            best = mid
                            lo = mid
                        else:
                            hi = mid
                    except Exception:
                        hi = mid

                results.append(
                    {
                        "Post": f"{post.plies}-ply {post.size}",
                        "Max Spacing": f"{best:.1f} ft" if best > 0 else "N/A",
                        "Mr (kN-m)": f"{post.Mr:.2f}",
                    }
                )

            st.table(results)

    st.divider()

    st.subheader("About")
    st.markdown("""
    **Design Codes:**
    - NBCC-2010 (Snow & Wind)
    - CSA O86-09 (Wood Design)
    
    **Load Combinations:**
    - LC3: 1.25D + 1.5S + 0.4W
    - LC5: 1.25D + 1.4W + 0.5S
    """)
