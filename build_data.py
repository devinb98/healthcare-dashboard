"""
Build the small, bundled data slice the dashboard reads.

Reads two CMS Nursing Home Compare files (Oct 2024) and the SNF VBP
facility-performance file, keeps only the columns the dashboard needs, and
writes a compact parquet into ./data/. Run once; the parquet is committed so
the deployed app needs no Snowflake and no raw data.

    python build_data.py            # uses the default source dir below
    SRC=/path/to/csvs python build_data.py
"""

import os
from pathlib import Path

import pandas as pd

SRC = Path(os.environ.get("SRC", Path.home() / "Desktop/Projects/healthdataproj"))
OUT = Path(__file__).parent / "data"
OUT.mkdir(exist_ok=True)

CCN = "CMS Certification Number (CCN)"

provider_cols = {
    CCN: "ccn",
    "Provider Name": "name",
    "State": "state",
    "Ownership Type": "ownership",
    "Number of Certified Beds": "beds",
    "Average Number of Residents per Day": "residents_per_day",
    "Overall Rating": "overall_rating",
    "Staffing Rating": "staffing_rating",
    "Reported RN Staffing Hours per Resident per Day": "rn_hprd",
    "Reported Total Nurse Staffing Hours per Resident per Day": "total_hprd",
    "Total nursing staff turnover": "nurse_turnover",
}

vbp_cols = {
    CCN: "ccn",
    "Performance Period: FY 2022 Risk-Standardized Readmission Rate": "readmission_rate",
    "Performance Score": "performance_score",
    "SNF VBP Program Ranking": "vbp_rank",
}


def read_csv(name: str, cols: dict) -> pd.DataFrame:
    path = SRC / name
    df = pd.read_csv(path, dtype={CCN: str}, usecols=list(cols), encoding="latin-1", low_memory=False)
    return df.rename(columns=cols)


def main() -> None:
    prov = read_csv("NH_ProviderInfo_Oct2024.csv", provider_cols)
    vbp = read_csv("FY_2024_SNF_VBP_Facility_Performance.csv", vbp_cols)

    df = prov.merge(vbp, on="ccn", how="left")

    # Coerce numerics; blanks / footnote markers become NaN.
    numeric = [
        "beds", "residents_per_day", "overall_rating", "staffing_rating",
        "rn_hprd", "total_hprd", "nurse_turnover", "readmission_rate",
        "performance_score", "vbp_rank",
    ]
    for c in numeric:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    # turnover is already a percent in the source; readmission is a fraction → percent
    df["nurse_turnover"] = df["nurse_turnover"].round(1)
    df["readmission_rate"] = (df["readmission_rate"] * 100).round(2)

    # Occupancy = residents per day / certified beds
    df["occupancy"] = (df["residents_per_day"] / df["beds"] * 100).round(1)
    df.loc[(df["beds"] <= 0) | (df["occupancy"] > 110), "occupancy"] = pd.NA

    df = df[df["state"].str.len() == 2]  # drop territories-with-odd-codes / blanks
    df = df.dropna(subset=["overall_rating"])

    facilities = df[[
        "ccn", "name", "state", "ownership", "beds", "residents_per_day",
        "occupancy", "overall_rating", "staffing_rating", "rn_hprd",
        "total_hprd", "nurse_turnover", "readmission_rate", "performance_score",
    ]].reset_index(drop=True)

    facilities.to_parquet(OUT / "facilities.parquet", index=False)

    # Per-state rollup for the national map / bars.
    state = (
        facilities.groupby("state")
        .agg(
            facilities=("ccn", "count"),
            avg_overall=("overall_rating", "mean"),
            avg_total_hprd=("total_hprd", "mean"),
            avg_readmission=("readmission_rate", "mean"),
            avg_occupancy=("occupancy", "mean"),
            avg_turnover=("nurse_turnover", "mean"),
        )
        .round(2)
        .reset_index()
    )
    state.to_parquet(OUT / "state_summary.parquet", index=False)

    print(f"facilities: {len(facilities):,} rows -> {OUT/'facilities.parquet'}")
    print(f"states:     {len(state):,} rows -> {OUT/'state_summary.parquet'}")
    print("parquet sizes:",
          {p.name: f"{p.stat().st_size/1e6:.2f} MB" for p in OUT.glob('*.parquet')})


if __name__ == "__main__":
    main()
