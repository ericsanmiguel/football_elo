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
from .worldcup import export_worldcup_json

# World Cup winners (hardcoded historical data)
MEN_WC_WINNERS = {
    "Brazil": [1958, 1962, 1970, 1994, 2002],
    "Germany": [1954, 1974, 1990, 2014],
    "Italy": [1934, 1938, 1982, 2006],
    "Argentina": [1978, 1986, 2022],
    "France": [1998, 2018],
    "Uruguay": [1930, 1950],
    "England": [1966],
    "Spain": [2010],
}

WOMEN_WC_WINNERS = {
    "United States": [1991, 1999, 2015, 2019],
    "Germany": [2003, 2007],
    "Norway": [1995],
    "Japan": [2011],
    "Spain": [2023],
}

DOCS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "data"

WOMEN_TOURNAMENTS = [
    {"name": "After 2023 WWC", "date": "2023-08-20"},
    {"name": "After 2019 WWC", "date": "2019-07-07"},
    {"name": "After 2015 WWC", "date": "2015-07-05"},
    {"name": "After 2011 WWC", "date": "2011-07-17"},
    {"name": "After 2007 WWC", "date": "2007-09-30"},
    {"name": "After 2003 WWC", "date": "2003-10-12"},
    {"name": "After 1999 WWC", "date": "1999-07-10"},
    {"name": "After 1995 WWC", "date": "1995-06-18"},
    {"name": "After 1991 WWC", "date": "1991-11-30"},
]

MEN_TOURNAMENTS = [
    {"name": "After 2022 WC", "date": "2022-12-18"},
    {"name": "After 2018 WC", "date": "2018-07-15"},
    {"name": "After 2014 WC", "date": "2014-07-13"},
    {"name": "After 2010 WC", "date": "2010-07-11"},
    {"name": "After 2006 WC", "date": "2006-07-09"},
    {"name": "After 2002 WC", "date": "2002-06-30"},
    {"name": "After 1998 WC", "date": "1998-07-12"},
    {"name": "After 1994 WC", "date": "1994-07-17"},
    {"name": "After 1990 WC", "date": "1990-07-08"},
    {"name": "After 1986 WC", "date": "1986-06-29"},
    {"name": "After 1982 WC", "date": "1982-07-11"},
    {"name": "After 1978 WC", "date": "1978-06-25"},
    {"name": "After 1974 WC", "date": "1974-07-07"},
    {"name": "After 1970 WC", "date": "1970-06-21"},
    {"name": "After 1966 WC", "date": "1966-07-30"},
    {"name": "After 1962 WC", "date": "1962-06-17"},
    {"name": "After 1958 WC", "date": "1958-06-29"},
    {"name": "After 1954 WC", "date": "1954-07-04"},
    {"name": "After 1950 WC", "date": "1950-07-16"},
    {"name": "After 1938 WC", "date": "1938-06-19"},
    {"name": "After 1934 WC", "date": "1934-06-10"},
    {"name": "After 1930 WC", "date": "1930-07-30"},
]

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


# Non-FIFA teams to exclude from rankings (CONIFA, island games, historical, etc.)
NON_FIFA_SLUGS = {
    # CONIFA / non-FIFA entities
    "abkhazia", "alderney", "ambazonia", "andalusia", "arameans-suryoye",
    "artsakh", "asturias", "aymara", "barawa", "basque-country",
    "catalonia", "chameria", "chagos-islands", "darfur", "ellan-vannin",
    "felvidek", "froya", "gozo", "hitra", "iraqi-kurdistan",
    "isle-of-man", "isle-of-wight", "jersey", "guernsey", "kabylia",
    "kernow", "luhansk", "mapuche", "matabeleland", "menorca",
    "northern-cyprus", "occitania", "orkney", "padania", "panjab",
    "prince-edward-island", "raetia", "rhodes", "roma", "saare-county",
    "sapmi", "shetland", "shetland-islands", "somaliland", "south-ossetia",
    "surrey", "szekely-land", "tamil-eelam", "tibet", "tuvalu",
    "western-armenia", "western-isles", "western-sahara", "ynys-mon",
    "zazaland", "gotland", "aland", "aland-islands",
    # Overseas territories (not separate FIFA members)
    "reunion", "martinique", "guadeloupe", "mayotte",
    "bonaire", "great-britain",
    # Historical / defunct (already filtered by inactive cutoff, but just in case)
    "czechoslovakia", "yugoslavia", "fr-yugoslavia", "serbia-and-montenegro",
    "netherlands-antilles",
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


def _compute_rank_history(
    elo: EloSystem, start_date: str = "1990-01-01"
) -> dict[str, list[dict]]:
    """Compute rank at each match date for every team (from start_date onward).

    Returns {team_name: [{"date": ..., "rk": rank}, ...]}.
    """
    history_df = elo.get_history_dataframe()
    all_dates = sorted(history_df[history_df["date"] >= start_date]["date"].unique())

    # Build running ratings: at each date, what is each team's rating?
    running_ratings: dict[str, float] = {}
    rank_history: dict[str, list[dict]] = {team: [] for team in elo.ratings}

    # Process all history entries chronologically
    date_groups = history_df.groupby("date")
    sorted_dates = sorted(date_groups.groups.keys())

    for date in sorted_dates:
        group = date_groups.get_group(date)

        # Add first-time teams with their pre-match rating
        for _, row in group.iterrows():
            if row["team"] not in running_ratings:
                running_ratings[row["team"]] = row["rating_before"]

        if date >= pd.Timestamp(start_date):
            # Compute ranks BEFORE this date's matches (pre-match ranking)
            fifa_ratings = [
                (team, rating) for team, rating in running_ratings.items()
                if slugify(team) not in NON_FIFA_SLUGS
            ]
            sorted_teams = sorted(fifa_ratings, key=lambda x: x[1], reverse=True)
            for rank_idx, (team, _rating) in enumerate(sorted_teams, 1):
                if team in group["team"].values:
                    rank_history[team].append({
                        "date": str(date.date()),
                        "rk": rank_idx,
                    })

        # THEN update running ratings with post-match results
        for _, row in group.iterrows():
            running_ratings[row["team"]] = row["rating_after"]

    return rank_history


def _compute_monthly_snapshots(elo: EloSystem, start_date: str = "1990-01-01") -> list[dict]:
    """Compute ranking snapshots at the 1st of each month from 1990 onward.

    Returns a list of {"date": "YYYY-MM-01", "teams": [{"team", "slug", "rating", "rank"}, ...]}.
    """
    history_df = elo.get_history_dataframe()
    running_ratings: dict[str, float] = {}

    date_groups = history_df.groupby("date")
    sorted_dates = sorted(date_groups.groups.keys())

    snapshots = []
    next_snapshot = pd.Timestamp(start_date)

    for date in sorted_dates:
        group = date_groups.get_group(date)
        for _, row in group.iterrows():
            running_ratings[row["team"]] = row["rating_after"]

        # Emit snapshots for any months we've passed
        while next_snapshot <= date and next_snapshot <= sorted_dates[-1]:
            # Filter to teams with >= MIN_MATCHES and recent activity
            team_counts = history_df[
                history_df["date"] <= date
            ].groupby("team").size()

            fifa_ratings = [
                (team, rating) for team, rating in running_ratings.items()
                if slugify(team) not in NON_FIFA_SLUGS
            ]
            sorted_teams = sorted(fifa_ratings, key=lambda x: x[1], reverse=True)
            ranked = []
            rank = 0
            for team, rating in sorted_teams:
                count = team_counts.get(team, 0)
                if count < 10:  # lighter filter for historical
                    continue
                rank += 1
                ranked.append({
                    "t": team,
                    "s": slugify(team),
                    "r": round(rating, 1),
                    "rk": rank,
                })
                if rank >= 50:  # top 50 per snapshot
                    break

            snapshots.append({
                "date": str(next_snapshot.date()),
                "teams": ranked,
            })
            # Advance to next month
            if next_snapshot.month == 12:
                next_snapshot = pd.Timestamp(f"{next_snapshot.year + 1}-01-01")
            else:
                next_snapshot = pd.Timestamp(
                    f"{next_snapshot.year}-{next_snapshot.month + 1:02d}-01"
                )

    return snapshots


def export_historical_rankings(
    elo: EloSystem, output_dir: Path, start_date: str = "1990-01-01"
) -> None:
    """Export monthly ranking snapshots as JSON."""
    snapshots = _compute_monthly_snapshots(elo, start_date)
    (output_dir / "historical_rankings.json").write_text(
        json.dumps(snapshots, separators=(",", ":")), encoding="utf-8"
    )


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
    elo: EloSystem, rank_history: dict[str, list[dict]], output_dir: Path,
    gender: str = "women",
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

        # Filter: minimum matches, recent activity, and FIFA members only
        slug = slugify(team)
        if matches < MIN_MATCHES:
            continue
        last_match_date = str(team_hist.iloc[-1]["date"].date())
        if last_match_date < INACTIVE_CUTOFF:
            continue
        if slug in NON_FIFA_SLUGS:
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

        wc_winners = MEN_WC_WINNERS if gender == "men" else WOMEN_WC_WINNERS
        wc_wins = wc_winners.get(team, [])
        if wc_wins:
            entry["wc_stars"] = len(wc_wins)

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
    elo: EloSystem, rank_history: dict[str, list[dict]], output_dir: Path,
    gender: str = "women",
) -> None:
    """Export per-team history JSON files with smoothed ratings and rank."""
    history_dir = output_dir / "history"
    history_dir.mkdir(parents=True, exist_ok=True)

    history_df = elo.get_history_dataframe()

    # Build opponent lookup: (date, team, opponent) -> (rating_before, rank)
    # For each record, the "opponent's" data is the record where team=opponent, opponent=team
    opp_lookup = {}
    for _, r in history_df.iterrows():
        key = (str(r["date"].date()), r["opponent"], r["team"])
        opp_lookup[key] = r["rating_before"]

    # Build rank lookup: (team, date) -> rank
    all_rank_lookup = {}
    for team_name, ranks in rank_history.items():
        for entry in ranks:
            all_rank_lookup[(team_name, entry["date"])] = entry["rk"]

    for team in elo.ratings:
        team_hist = history_df[history_df["team"] == team].copy()
        slug = slugify(team)

        records = []
        for _, r in team_hist.iterrows():
            date_str = str(r["date"].date())
            rec = {
                "date": date_str,
                "opponent": r["opponent"],
                "ts": int(r["team_score"]),
                "os": int(r["opponent_score"]),
                "tournament": r["tournament"],
                "k": int(r["k_factor"]),
                "rb": round(r["rating_before"], 1),
                "ra": round(r["rating_after"], 1),
                "rc": round(r["rating_change"], 1),
            }
            # Add opponent rating and rank for World Cup matches
            if r["tournament"] == "FIFA World Cup":
                opp_key = (date_str, team, r["opponent"])
                orb = opp_lookup.get(opp_key)
                if orb is not None:
                    rec["orb"] = round(orb, 1)
                ork = all_rank_lookup.get((r["opponent"], date_str))
                if ork is not None:
                    rec["ork"] = ork
            records.append(rec)

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

        # Compute best/worst rank
        team_ranks = rank_history.get(team, [])
        rank_values = [r["rk"] for r in team_ranks]
        best_rank = min(rank_values) if rank_values else None
        worst_rank = max(rank_values) if rank_values else None

        # First and last time best rank was achieved
        best_rank_dates = [r["date"] for r in team_ranks if r["rk"] == best_rank] if best_rank is not None else []
        best_rank_first = best_rank_dates[0] if best_rank_dates else ""
        best_rank_last = best_rank_dates[-1] if best_rank_dates else ""

        worst_rank_dates = [r["date"] for r in team_ranks if r["rk"] == worst_rank] if worst_rank is not None else []
        worst_rank_first = worst_rank_dates[0] if worst_rank_dates else ""
        worst_rank_last = worst_rank_dates[-1] if worst_rank_dates else ""

        # Top 5 wins and worst 5 losses by rating change
        sorted_by_rc = sorted(records, key=lambda r: r["rc"])
        worst_losses = sorted_by_rc[:5]
        top_wins = sorted_by_rc[-5:][::-1]

        # World Cup data
        wc_winners = MEN_WC_WINNERS if gender == "men" else WOMEN_WC_WINNERS
        wc_wins = wc_winners.get(team, [])
        wc_stars = len(wc_wins)

        # World Cup overall record (from match history)
        wc_matches = [r for r in records if r["tournament"] == "FIFA World Cup"]
        wc_w = sum(1 for r in wc_matches if r["ts"] > r["os"])
        wc_d = sum(1 for r in wc_matches if r["ts"] == r["os"])
        wc_l = sum(1 for r in wc_matches if r["ts"] < r["os"])

        data = {
            "team": team,
            "slug": slug,
            "wc_stars": wc_stars,
            "wc_wins": wc_wins,
            "wc_record": {"w": wc_w, "d": wc_d, "l": wc_l} if wc_matches else None,
            "best_rank": best_rank,
            "best_rank_first": best_rank_first,
            "best_rank_last": best_rank_last,
            "worst_rank": worst_rank,
            "worst_rank_first": worst_rank_first,
            "worst_rank_last": worst_rank_last,
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


def export_tournaments_json(gender: str, output_dir: Path) -> None:
    """Export major tournament dates for quick-jump buttons."""
    tournaments = WOMEN_TOURNAMENTS if gender == "women" else MEN_TOURNAMENTS
    (output_dir / "tournaments.json").write_text(
        json.dumps(tournaments, separators=(",", ":")), encoding="utf-8"
    )


def export_squads_json(output_dir: Path, year: int = 2026) -> None:
    """Export per-team position ratings and player lists for the Squads tab.

    Each player is rated 0-100 within his position group; each team gets
    GK/DEF/MID/FWD scores (relative to the other teams' units) plus an average.
    Display-only: this does not feed the match predictions.
    """
    from .squad_strength import (
        GROUP_ORDER,
        load_tournament_squads,
        player_position_ratings,
        team_position_scores,
    )
    from .worldcup import GROUPS_2026

    df = load_tournament_squads(year)
    rated = player_position_ratings(df)
    scores = team_position_scores(rated)
    team_group = {t: g for g, teams in GROUPS_2026.items() for t in teams}
    order = {g: i for i, g in enumerate(GROUP_ORDER)}

    teams: dict[str, dict] = {}
    for team, sub in rated.groupby("team"):
        players = []
        for _, r in sub.iterrows():
            players.append({
                "player": r["player"],
                "pos": r["pgroup"],
                "pos_code": r["position_code"],
                "club": None if pd.isna(r.get("club")) else r["club"],
                "age": None if pd.isna(r["age_at_kickoff"]) else round(float(r["age_at_kickoff"]), 1),
                "value": None if pd.isna(r["value_at_kickoff"]) else int(r["value_at_kickoff"]),
                "rating": None if pd.isna(r["rating"]) else r["rating"],
            })
        players.sort(key=lambda p: (order.get(p["pos"], 9), -(p["rating"] or 0)))
        teams[team] = {
            "slug": slugify(team),
            "group": team_group.get(team),
            "scores": scores.get(team, {}),
            "players": players,
        }

    data = {
        "tournament": "2026 FIFA World Cup",
        "kickoff": "2026-06-11",
        "position_groups": GROUP_ORDER,
        "teams": teams,
    }
    (output_dir / "squads2026.json").write_text(
        json.dumps(data, separators=(",", ":")), encoding="utf-8"
    )


def export_all(
    elo: EloSystem, gender: str = "women", base_dir: Path = DOCS_DIR
) -> None:
    """Export all JSON files for the website.

    Gender-specific files go to base_dir/{gender}/.
    Shared files (colors, flags) go to base_dir/.
    """
    output_dir = base_dir / gender
    output_dir.mkdir(parents=True, exist_ok=True)
    start_date = "1900-01-01" if gender == "men" else "1990-01-01"
    print(f"  Exporting {gender} to {output_dir}/")

    print("    Computing rank history...")
    rank_history = _compute_rank_history(elo, start_date)

    export_rankings_json(elo, rank_history, output_dir, gender)
    print("    rankings.json")

    # Shared files go to base_dir (only write once)
    if not (base_dir / "team_colors.json").exists() or gender == "women":
        export_team_colors_json(base_dir)
        print("    team_colors.json (shared)")
        export_team_flags_json(base_dir)
        print("    team_flags.json (shared)")

    export_team_histories(elo, rank_history, output_dir, gender)
    print(f"    history/ ({len(elo.ratings)} team files)")

    export_history_top_n(elo, 20, output_dir)
    print("    history_top20.json")

    export_tournaments_json(gender, output_dir)
    print("    tournaments.json")

    print("    Computing historical rankings...")
    export_historical_rankings(elo, output_dir, start_date)
    print("    historical_rankings.json")

    if gender == "men":
        print("    Computing World Cup 2026 predictions...")
        export_worldcup_json(elo, output_dir)
        print("    worldcup2026.json")
        export_squads_json(output_dir)
        print("    squads2026.json")
