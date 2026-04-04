"""Data download and loading from GitHub."""

from pathlib import Path

import pandas as pd
import requests

from .config import DATA_DIR, RESULTS_URL, SHOOTOUTS_URL

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


def download_data(data_dir: Path = DATA_DIR, force: bool = False) -> None:
    """Download results.csv and shootouts.csv from GitHub."""
    download_file(RESULTS_URL, data_dir / "results.csv", force=force)
    download_file(SHOOTOUTS_URL, data_dir / "shootouts.csv", force=force)


def load_results(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load results.csv into a DataFrame."""
    df = pd.read_csv(
        data_dir / "results.csv",
        parse_dates=["date"],
        dtype={
            "home_team": str,
            "away_team": str,
            "home_score": int,
            "away_score": int,
            "tournament": str,
            "city": str,
            "country": str,
        },
    )
    # Normalize neutral column (may be TRUE/FALSE strings)
    df["neutral"] = df["neutral"].astype(str).str.upper() == "TRUE"
    # Normalize successor state names
    df["home_team"] = df["home_team"].replace(TEAM_NAME_MAP)
    df["away_team"] = df["away_team"].replace(TEAM_NAME_MAP)
    return df.sort_values("date").reset_index(drop=True)


def load_shootouts(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load shootouts.csv into a DataFrame."""
    path = data_dir / "shootouts.csv"
    if not path.exists():
        return pd.DataFrame(columns=["date", "home_team", "away_team", "winner"])
    df = pd.read_csv(path, parse_dates=["date"])
    for col in ["home_team", "away_team", "winner"]:
        if col in df.columns:
            df[col] = df[col].replace(TEAM_NAME_MAP)
    return df


def load_all(data_dir: Path = DATA_DIR) -> pd.DataFrame:
    """Load results and merge with shootout data."""
    results = load_results(data_dir)
    shootouts = load_shootouts(data_dir)

    # Left join to add shootout_winner column
    merged = results.merge(
        shootouts[["date", "home_team", "away_team", "winner"]].rename(
            columns={"winner": "shootout_winner"}
        ),
        on=["date", "home_team", "away_team"],
        how="left",
    )
    return merged
