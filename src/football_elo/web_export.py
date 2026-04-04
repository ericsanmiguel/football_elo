"""Export Elo data as JSON files for the website."""

import json
import re
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

from .config import OUTPUT_DIR
from .output import TEAM_COLORS
from .pipeline import EloSystem

DOCS_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "data"

# Team slug -> ISO 3166-1 alpha-2 code for flagcdn.com
TEAM_FLAGS = {
    "afghanistan": "af", "albania": "al", "algeria": "dz", "american-samoa": "as",
    "andorra": "ad", "angola": "ao", "antigua-and-barbuda": "ag", "argentina": "ar",
    "armenia": "am", "aruba": "aw", "australia": "au", "austria": "at",
    "azerbaijan": "az", "bahamas": "bs", "bahrain": "bh", "bangladesh": "bd",
    "barbados": "bb", "belarus": "by", "belgium": "be", "belize": "bz",
    "benin": "bj", "bermuda": "bm", "bhutan": "bt", "bolivia": "bo",
    "bosnia-and-herzegovina": "ba", "botswana": "bw", "brazil": "br",
    "british-virgin-islands": "vg", "bulgaria": "bg", "burkina-faso": "bf",
    "burundi": "bi", "cambodia": "kh", "cameroon": "cm", "canada": "ca",
    "cape-verde": "cv", "cayman-islands": "ky", "central-african-republic": "cf",
    "chad": "td", "chile": "cl", "china-pr": "cn", "colombia": "co",
    "comoros": "km", "congo": "cg", "cook-islands": "ck", "costa-rica": "cr",
    "croatia": "hr", "cuba": "cu", "curacao": "cw", "cyprus": "cy",
    "czech-republic": "cz", "denmark": "dk", "djibouti": "dj",
    "dominica": "dm", "dominican-republic": "do", "dr-congo": "cd",
    "ecuador": "ec", "egypt": "eg", "el-salvador": "sv",
    "england": "gb-eng", "equatorial-guinea": "gq", "eritrea": "er",
    "estonia": "ee", "eswatini": "sz", "ethiopia": "et",
    "faroe-islands": "fo", "fiji": "fj", "finland": "fi", "france": "fr",
    "gabon": "ga", "gambia": "gm", "georgia": "ge", "germany": "de",
    "ghana": "gh", "gibraltar": "gi", "greece": "gr", "greenland": "gl",
    "grenada": "gd", "guam": "gu", "guatemala": "gt", "guinea": "gn",
    "guinea-bissau": "gw", "guyana": "gy", "haiti": "ht", "honduras": "hn",
    "hong-kong": "hk", "hungary": "hu", "iceland": "is", "india": "in",
    "indonesia": "id", "iran": "ir", "iraq": "iq", "israel": "il",
    "italy": "it", "ivory-coast": "ci", "jamaica": "jm", "japan": "jp",
    "jordan": "jo", "kazakhstan": "kz", "kenya": "ke", "kiribati": "ki",
    "kosovo": "xk", "kuwait": "kw", "kyrgyzstan": "kg", "laos": "la",
    "latvia": "lv", "lebanon": "lb", "lesotho": "ls", "liberia": "lr",
    "libya": "ly", "liechtenstein": "li", "lithuania": "lt",
    "luxembourg": "lu", "macau": "mo", "madagascar": "mg", "malawi": "mw",
    "malaysia": "my", "maldives": "mv", "mali": "ml", "malta": "mt",
    "mauritania": "mr", "mauritius": "mu", "mexico": "mx", "moldova": "md",
    "mongolia": "mn", "montenegro": "me", "morocco": "ma", "mozambique": "mz",
    "myanmar": "mm", "namibia": "na", "nepal": "np", "netherlands": "nl",
    "new-caledonia": "nc", "new-zealand": "nz", "nicaragua": "ni",
    "niger": "ne", "nigeria": "ng", "north-korea": "kp",
    "north-macedonia": "mk", "northern-ireland": "gb-nir", "norway": "no",
    "pakistan": "pk", "palestine": "ps", "panama": "pa",
    "papua-new-guinea": "pg", "paraguay": "py", "peru": "pe",
    "philippines": "ph", "poland": "pl", "portugal": "pt",
    "puerto-rico": "pr", "qatar": "qa", "republic-of-ireland": "ie",
    "romania": "ro", "russia": "ru", "rwanda": "rw",
    "saint-kitts-and-nevis": "kn", "saint-lucia": "lc",
    "saint-vincent-and-the-grenadines": "vc", "samoa": "ws",
    "sao-tome-and-principe": "st", "saudi-arabia": "sa",
    "scotland": "gb-sct", "senegal": "sn", "serbia": "rs",
    "seychelles": "sc", "sierra-leone": "sl", "singapore": "sg",
    "slovakia": "sk", "slovenia": "si", "solomon-islands": "sb",
    "south-africa": "za", "south-korea": "kr", "south-sudan": "ss",
    "spain": "es", "sri-lanka": "lk", "sudan": "sd", "suriname": "sr",
    "sweden": "se", "switzerland": "ch", "syria": "sy", "tahiti": "pf",
    "taiwan": "tw", "tajikistan": "tj", "tanzania": "tz", "thailand": "th",
    "timor-leste": "tl", "togo": "tg", "tonga": "to",
    "trinidad-and-tobago": "tt", "tunisia": "tn", "turkey": "tr",
    "turkmenistan": "tm", "turks-and-caicos-islands": "tc",
    "uganda": "ug", "ukraine": "ua", "united-arab-emirates": "ae",
    "united-states": "us", "united-states-virgin-islands": "vi",
    "uruguay": "uy", "uzbekistan": "uz", "vanuatu": "vu",
    "venezuela": "ve", "vietnam": "vn", "wales": "gb-wls",
    "zambia": "zm", "zimbabwe": "zw",
}


def slugify(name: str) -> str:
    """Convert team name to URL-safe slug."""
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s


def _compute_rank_history(elo: EloSystem) -> dict[str, list[dict]]:
    """Compute rank at each match date for every team (from 1990 onward).

    Returns {team_name: [{"date": ..., "rk": rank}, ...]}.
    """
    history_df = elo.get_history_dataframe()
    # Get unique dates from 1990 onward
    all_dates = sorted(history_df[history_df["date"] >= "1990-01-01"]["date"].unique())

    # Build running ratings: at each date, what is each team's rating?
    running_ratings: dict[str, float] = {}
    rank_history: dict[str, list[dict]] = {team: [] for team in elo.ratings}

    # Process all history entries chronologically
    date_groups = history_df.groupby("date")
    sorted_dates = sorted(date_groups.groups.keys())

    for date in sorted_dates:
        group = date_groups.get_group(date)
        # Update running ratings from this date's matches
        for _, row in group.iterrows():
            running_ratings[row["team"]] = row["rating_after"]

        if date < pd.Timestamp("1990-01-01"):
            continue

        # Compute ranks at this date
        sorted_teams = sorted(
            running_ratings.items(), key=lambda x: x[1], reverse=True
        )
        for rank_idx, (team, _rating) in enumerate(sorted_teams, 1):
            # Only record if this team played on this date
            if team in group["team"].values:
                rank_history[team].append({
                    "date": str(date.date()),
                    "rk": rank_idx,
                })

    return rank_history


def _compute_smoothed_ratings(
    history_records: list[dict], window_days: int = 365
) -> list[float]:
    """Compute smoothed ratings using a rolling average."""
    if not history_records:
        return []
    dates = pd.to_datetime([r["date"] for r in history_records])
    ratings = pd.Series([r["ra"] for r in history_records], index=dates)
    # Resample to daily, forward-fill, rolling mean, then pick original dates
    daily = ratings.resample("D").last().ffill()
    smoothed = daily.rolling(window=window_days, center=True, min_periods=1).mean()
    # Get smoothed values at original match dates
    result = []
    for d in dates:
        val = smoothed.get(d)
        result.append(round(float(val), 1) if val is not None else None)
    return result


def export_team_flags_json(output_dir: Path) -> None:
    """Export team flags mapping."""
    (output_dir / "team_flags.json").write_text(
        json.dumps(TEAM_FLAGS, separators=(",", ":")), encoding="utf-8"
    )


MIN_MATCHES = 20
INACTIVE_CUTOFF = "2016-01-01"


def export_rankings_json(
    elo: EloSystem, rank_history: dict[str, list[dict]], output_dir: Path
) -> None:
    """Export current rankings as JSON.

    Filters out teams with fewer than MIN_MATCHES matches or whose last
    match was before INACTIVE_CUTOFF (removes defunct teams like Yugoslavia).
    """
    rankings = elo.get_current_rankings()
    history_df = elo.get_history_dataframe()

    teams = []
    filtered_rank = 0
    for _rank, row in rankings.iterrows():
        team = row["team"]
        team_hist = history_df[history_df["team"] == team]
        matches = len(team_hist)

        # Filter: minimum matches and recent activity
        if matches < MIN_MATCHES:
            continue
        last_match_date = str(team_hist.iloc[-1]["date"].date())
        if last_match_date < INACTIVE_CUTOFF:
            continue

        filtered_rank += 1
        last_change = team_hist.iloc[-1]["rating_change"] if matches > 0 else 0

        peak_rating = team_hist["rating_after"].max() if matches > 0 else row["rating"]
        peak_date = ""
        if matches > 0:
            peak_idx = team_hist["rating_after"].idxmax()
            peak_date = str(team_hist.loc[peak_idx, "date"].date())

        # Best/worst rank from rank_history
        team_ranks = rank_history.get(team, [])
        best_rank = min((r["rk"] for r in team_ranks), default=None)
        worst_rank = max((r["rk"] for r in team_ranks), default=None)

        entry = {
            "rank": filtered_rank,
            "team": team,
            "slug": slugify(team),
            "rating": round(row["rating"], 1),
            "rating_change": round(last_change, 1),
            "matches_played": matches,
            "peak_rating": round(peak_rating, 1),
            "peak_date": peak_date,
        }
        if best_rank is not None:
            entry["best_rank"] = best_rank
        if worst_rank is not None:
            entry["worst_rank"] = worst_rank

        teams.append(entry)

    last_updated = str(history_df["date"].max().date()) if len(history_df) > 0 else ""

    data = {"last_updated": last_updated, "teams": teams}
    (output_dir / "rankings.json").write_text(
        json.dumps(data, separators=(",", ":")), encoding="utf-8"
    )


def export_team_colors_json(output_dir: Path) -> None:
    """Export team colors mapping."""
    colors = {slugify(team): color for team, color in TEAM_COLORS.items()}
    (output_dir / "team_colors.json").write_text(
        json.dumps(colors, separators=(",", ":")), encoding="utf-8"
    )


def export_team_histories(
    elo: EloSystem, rank_history: dict[str, list[dict]], output_dir: Path
) -> None:
    """Export per-team history JSON files with smoothed ratings and rank."""
    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    history_df = elo.get_history_dataframe()

    for team in elo.ratings:
        team_hist = history_df[history_df["team"] == team].copy()
        slug = slugify(team)

        records = []
        for _, r in team_hist.iterrows():
            records.append({
                "date": str(r["date"].date()),
                "opponent": r["opponent"],
                "ts": int(r["team_score"]),
                "os": int(r["opponent_score"]),
                "tournament": r["tournament"],
                "k": int(r["k_factor"]),
                "rb": round(r["rating_before"], 1),
                "ra": round(r["rating_after"], 1),
                "rc": round(r["rating_change"], 1),
            })

        # Add smoothed ratings
        smoothed = _compute_smoothed_ratings(records)
        for i, rs in enumerate(smoothed):
            if rs is not None:
                records[i]["rs"] = rs

        # Add rank at each match date
        team_rank_hist = {r["date"]: r["rk"] for r in rank_history.get(team, [])}
        for rec in records:
            rk = team_rank_hist.get(rec["date"])
            if rk is not None:
                rec["rk"] = rk

        # Compute best/worst rank from 1990
        rank_values = [r["rk"] for r in rank_history.get(team, [])]
        best_rank = min(rank_values) if rank_values else None
        worst_rank = max(rank_values) if rank_values else None
        best_rank_date = next(
            (r["date"] for r in rank_history.get(team, []) if r["rk"] == best_rank), ""
        ) if best_rank is not None else ""
        worst_rank_date = next(
            (r["date"] for r in rank_history.get(team, []) if r["rk"] == worst_rank), ""
        ) if worst_rank is not None else ""

        # Top 5 wins and worst 5 losses by rating change
        sorted_by_rc = sorted(records, key=lambda r: r["rc"])
        worst_losses = sorted_by_rc[:5]
        top_wins = sorted_by_rc[-5:][::-1]

        data = {
            "team": team,
            "slug": slug,
            "best_rank": best_rank,
            "best_rank_date": best_rank_date,
            "worst_rank": worst_rank,
            "worst_rank_date": worst_rank_date,
            "top_wins": [
                {"date": r["date"], "opponent": r["opponent"], "ts": r["ts"],
                 "os": r["os"], "rc": r["rc"], "tournament": r["tournament"]}
                for r in top_wins
            ],
            "worst_losses": [
                {"date": r["date"], "opponent": r["opponent"], "ts": r["ts"],
                 "os": r["os"], "rc": r["rc"], "tournament": r["tournament"]}
                for r in worst_losses
            ],
            "history": records,
        }
        (history_dir / f"{slug}.json").write_text(
            json.dumps(data, separators=(",", ":")), encoding="utf-8"
        )


def export_history_top_n(elo: EloSystem, n: int, output_dir: Path) -> None:
    """Export bundled history for top N teams (date + rating only)."""
    rankings = elo.get_current_rankings()
    top_teams = rankings.head(n)["team"].tolist()
    history_df = elo.get_history_dataframe()

    result = {}
    for team in top_teams:
        team_hist = history_df[history_df["team"] == team]
        slug = slugify(team)
        result[slug] = {
            "team": team,
            "data": [
                {"date": str(r["date"].date()), "ra": round(r["rating_after"], 1)}
                for _, r in team_hist.iterrows()
            ],
        }

    (output_dir / "history_top20.json").write_text(
        json.dumps(result, separators=(",", ":")), encoding="utf-8"
    )


def export_tournaments_json(output_dir: Path) -> None:
    """Export major tournament dates for quick-jump buttons."""
    tournaments = [
        {"name": "2023 WWC Final", "date": "2023-08-20"},
        {"name": "2019 WWC Final", "date": "2019-07-07"},
        {"name": "2015 WWC Final", "date": "2015-07-05"},
        {"name": "2011 WWC Final", "date": "2011-07-17"},
        {"name": "2007 WWC Final", "date": "2007-09-30"},
        {"name": "2003 WWC Final", "date": "2003-10-12"},
        {"name": "1999 WWC Final", "date": "1999-07-10"},
        {"name": "1995 WWC Final", "date": "1995-06-18"},
        {"name": "1991 WWC Final", "date": "1991-11-30"},
        {"name": "2024 Olympics", "date": "2024-08-10"},
        {"name": "2021 Olympics", "date": "2021-08-06"},
    ]
    (output_dir / "tournaments.json").write_text(
        json.dumps(tournaments, separators=(",", ":")), encoding="utf-8"
    )


def export_all(elo: EloSystem, output_dir: Path = DOCS_DATA_DIR) -> None:
    """Export all JSON files for the website."""
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Exporting to {output_dir}/")

    print("    Computing rank history...")
    rank_history = _compute_rank_history(elo)

    export_rankings_json(elo, rank_history, output_dir)
    print("    rankings.json")

    export_team_colors_json(output_dir)
    print("    team_colors.json")

    export_team_flags_json(output_dir)
    print("    team_flags.json")

    export_team_histories(elo, rank_history, output_dir)
    print(f"    history/ ({len(elo.ratings)} team files)")

    export_history_top_n(elo, 20, output_dir)
    print("    history_top20.json")

    export_tournaments_json(output_dir)
    print("    tournaments.json")
