"""
U.S. Nursing Home Quality — a public Streamlit dashboard.

Reads the bundled, pre-aggregated parquet in ./data (built by build_data.py
from CMS Nursing Home Compare + SNF VBP, Oct 2024). No database, no secrets —
a public port of a Streamlit-in-Snowflake dashboard.
"""

from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

ACCENT = "#a6cb8c"  # sage, matches the portfolio's dark theme
# sage ramp for the ordinal star rating (dim → bright, legible on dark)
RATING_RANGE = ["#5f7a4b", "#7a9960", "#95b97a", "#b0d394", "#cbe9b2"]
DATA = Path(__file__).parent / "data"

st.set_page_config(
    page_title="Nursing Home Quality",
    page_icon="🏥",
    layout="wide",
)


@st.cache_data
def load() -> pd.DataFrame:
    df = pd.read_parquet(DATA / "facilities.parquet")
    df["owner_group"] = (
        df["ownership"].str.split(" - ").str[0].str.strip().fillna("Unknown")
    )
    return df


df = load()

# ---- header ----
st.title("U.S. Nursing Home Quality")
st.caption(
    f"{len(df):,} Medicare- & Medicaid-certified nursing homes · CMS Nursing Home "
    "Compare and SNF Value-Based Purchasing, October 2024. A public port of a "
    "Streamlit-in-Snowflake dashboard — the data is pre-aggregated and bundled, "
    "so there's no live database behind it."
)

# ---- filters ----
with st.sidebar:
    st.header("Filters")
    states = sorted(df["state"].unique())
    pick_states = st.multiselect("State", states, default=[])
    owners = sorted(df["owner_group"].unique())
    pick_owners = st.multiselect("Ownership", owners, default=[])
    st.markdown("---")
    st.markdown(
        "Built by **Devin Bajaj** · "
        "[portfolio](https://devinb98.github.io) · "
        "[source](https://github.com/devinb98/healthcare-dashboard)"
    )

view = df.copy()
if pick_states:
    view = view[view["state"].isin(pick_states)]
if pick_owners:
    view = view[view["owner_group"].isin(pick_owners)]

if view.empty:
    st.warning("No facilities match these filters. Widen the selection.")
    st.stop()

# ---- KPIs ----
c1, c2, c3, c4 = st.columns(4)
c1.metric("Facilities", f"{len(view):,}")
c2.metric("Avg overall rating", f"{view['overall_rating'].mean():.2f} ★")
c3.metric("Avg nurse staffing", f"{view['total_hprd'].mean():.2f} hrs/resident-day")
c4.metric("Avg 30-day readmission", f"{view['readmission_rate'].mean():.1f}%")

st.markdown("")


def bar_by_state(metric: str, title: str, fmt: str) -> alt.Chart:
    g = (
        view.groupby("state", as_index=False)[metric]
        .mean()
        .sort_values(metric, ascending=False)
    )
    return (
        alt.Chart(g)
        .mark_bar(color=ACCENT)
        .encode(
            x=alt.X("state:N", sort="-y", title=None),
            y=alt.Y(f"{metric}:Q", title=title),
            tooltip=[
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip(f"{metric}:Q", title=title, format=fmt),
            ],
        )
        .properties(height=300)
    )


tab1, tab2, tab3 = st.tabs(
    ["Staffing", "Readmission vs. staffing", "Ratings & occupancy"]
)

with tab1:
    st.subheader("Nurse staffing hours per resident-day")
    st.write(
        "How many hours of nursing care each resident receives per day — the "
        "clearest signal of how well-staffed a facility is."
    )
    left, right = st.columns([3, 2])
    with left:
        st.altair_chart(
            bar_by_state("total_hprd", "Total nurse hrs / resident-day", ".2f"),
            use_container_width=True,
        )
    with right:
        g = view.groupby("owner_group", as_index=False)["total_hprd"].mean()
        chart = (
            alt.Chart(g)
            .mark_bar(color=ACCENT)
            .encode(
                y=alt.Y("owner_group:N", sort="-x", title=None),
                x=alt.X("total_hprd:Q", title="Total nurse hrs / resident-day"),
                tooltip=[
                    alt.Tooltip("owner_group:N", title="Ownership"),
                    alt.Tooltip("total_hprd:Q", title="Hrs/res-day", format=".2f"),
                ],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)

with tab2:
    st.subheader("Does more staffing mean fewer readmissions?")
    st.write(
        "Each point is a facility: nurse staffing against its risk-standardized "
        "30-day hospital readmission rate. Color is the CMS overall star rating."
    )
    scatter_src = view.dropna(subset=["total_hprd", "readmission_rate"])
    if len(scatter_src) > 5000:
        scatter_src = scatter_src.sample(5000, random_state=0)
    scatter = (
        alt.Chart(scatter_src)
        .mark_circle(size=28, opacity=0.5)
        .encode(
            x=alt.X("total_hprd:Q", title="Total nurse hrs / resident-day",
                    scale=alt.Scale(domain=[0, 8])),
            y=alt.Y("readmission_rate:Q", title="30-day readmission rate (%)"),
            color=alt.Color(
                "overall_rating:O",
                title="Overall rating",
                scale=alt.Scale(range=RATING_RANGE),
            ),
            tooltip=[
                alt.Tooltip("name:N", title="Facility"),
                alt.Tooltip("state:N", title="State"),
                alt.Tooltip("total_hprd:Q", title="Hrs/res-day", format=".2f"),
                alt.Tooltip("readmission_rate:Q", title="Readmission %", format=".1f"),
                alt.Tooltip("overall_rating:O", title="Rating"),
            ],
        )
        .properties(height=440)
        .interactive()
    )
    st.altair_chart(scatter, use_container_width=True)

with tab3:
    left, right = st.columns(2)
    with left:
        st.subheader("Overall star ratings")
        g = (
            view.groupby("overall_rating", as_index=False)
            .size()
            .rename(columns={"size": "facilities"})
        )
        chart = (
            alt.Chart(g)
            .mark_bar(color=ACCENT)
            .encode(
                x=alt.X("overall_rating:O", title="CMS overall rating (stars)"),
                y=alt.Y("facilities:Q", title="Facilities"),
                tooltip=[
                    alt.Tooltip("overall_rating:O", title="Rating"),
                    alt.Tooltip("facilities:Q", title="Facilities", format=","),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)
    with right:
        st.subheader("Occupancy")
        st.write("Average daily residents as a share of certified beds.")
        occ = view.dropna(subset=["occupancy"]).copy()
        occ["bucket"] = (occ["occupancy"] // 5 * 5).astype(int)
        occ_g = (
            occ.groupby("bucket", as_index=False)
            .size()
            .rename(columns={"size": "facilities"})
        )
        chart = (
            alt.Chart(occ_g)
            .mark_bar(color=ACCENT)
            .encode(
                x=alt.X("bucket:Q", title="Occupancy (%)",
                        scale=alt.Scale(domain=[0, 110])),
                y=alt.Y("facilities:Q", title="Facilities"),
                tooltip=[
                    alt.Tooltip("bucket:Q", title="Occupancy ≥"),
                    alt.Tooltip("facilities:Q", title="Facilities", format=","),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

# ---- table ----
st.subheader("Facilities")
st.dataframe(
    view[[
        "name", "state", "owner_group", "beds", "occupancy", "overall_rating",
        "staffing_rating", "total_hprd", "readmission_rate", "nurse_turnover",
    ]]
    .sort_values("overall_rating", ascending=False)
    .rename(columns={
        "name": "Facility", "state": "State", "owner_group": "Ownership",
        "beds": "Beds", "occupancy": "Occupancy %", "overall_rating": "Overall ★",
        "staffing_rating": "Staffing ★", "total_hprd": "Nurse hrs/res-day",
        "readmission_rate": "Readmission %", "nurse_turnover": "Turnover %",
    }),
    use_container_width=True,
    hide_index=True,
    height=420,
)
