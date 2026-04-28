"""Data download and loading from GitHub."""

from pathlib import Path

import pandas as pd
import requests

from .config import DATA_DIR, DATA_SOURCES

# Normalize team names for successor states (treat as continuous teams)
TEAM_NAME_MAP = {
    "Macedonia": "North Macedonia",
    "FR Yugoslavia": "Serbia",
    "Serbia and Montenegro": "Serbia",
}


def download_file(url: str, dest: Path, force: bool = False) -> Path:
    """Download a file from URL to dest. Skips if file exists unless force=True."""
    if dest.exists() and not force:
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    dest.write_bytes(resp.content)
    return dest


def download_data(
    gender: str = "women", data_dir: Path = DATA_DIR, force: bool = False
) -> None:
    """Download results.csv and shootouts.csv from GitHub."""
    urls = DATA_SOURCES[gender]
    gender_dir = data_dir / gender
    download_file(urls["results"], gender_dir / "results.csv", force=force)
    download_file(urls["shootouts"], gender_dir / "shootouts.csv", force=force)


def load_results(gender: str = "women", data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load results.csv into a DataFrame."""
    df = pd.read_csv(
        data_dir / gender / "results.csv",
        parse_dates=["date"],
        dtype={
            "home_team": str,
            "away_team": str,
            "tournament": str,
            "city": str,
            "country": str,
        },
    )
    # Drop scheduled/unplayed matches (NA scores) before casting to int.
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    # Normalize neutral column (may be TRUE/FALSE strings)
    df["neutral"] = df["neutral"].astype(str).str.upper() == "TRUE"
    # Normalize successor state names
    df["home_team"] = df["home_team"].replace(TEAM_NAME_MAP)
    df["away_team"] = df["away_team"].replace(TEAM_NAME_MAP)
    return df.sort_values("date").reset_index(drop=True)


def load_shootouts(gender: str = "women", data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load shootouts.csv into a DataFrame."""
    path = data_dir / gender / "shootouts.csv"
    if not path.exists():
        return pd.DataFrame(columns=["date", "home_team", "away_team", "winner"])
    df = pd.read_csv(path, parse_dates=["date"])
    for col in ["home_team", "away_team", "winner"]:
        if col in df.columns:
            df[col] = df[col].replace(TEAM_NAME_MAP)
    return df


def load_all(gender: str = "women", data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load results and merge with shootout data."""
    results = load_results(gender, data_dir)
    shootouts = load_shootouts(gender, data_dir)

    # Left join to add shootout_winner column
    merged = results.merge(
        shootouts[["date", "home_team", "away_team", "winner"]].rename(
            columns={"winner": "shootout_winner"}
        ),
        on=["date", "home_team", "away_team"],
        how="left",
    )
    return merged
