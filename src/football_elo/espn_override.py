"""Live 2026 World Cup result overrides from ESPN's public scoreboard API.

Our canonical source, martj42/international_results, publishes new match
results about once a day -- usually the morning after the matches are played.
During the 2026 World Cup that means the site's Elo ratings and tournament
predictions lag the real results by up to a day.

This module pulls *finished* 2026 World Cup matches from ESPN's free,
keyless scoreboard endpoint and merges them into the match set **before**
Elo is computed, so finals show up within an hour or two of the whistle.
Once martj42 publishes the same match the next day, the override is deduped
away and the canonical row wins -- so this only ever fills the gap, it never
rewrites history.

The endpoint is undocumented but stable and widely used by hobby projects:
    https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates=YYYYMMDD

Design notes:
  * Team names are remapped to martj42's spellings so the merged rows match
    GROUPS_2026 (which collect_results() keys the predictions on).
  * The neutral flag is reproduced from martj42's convention: a 2026 World Cup
    match is non-neutral iff the home team is a host nation (US/Mexico/Canada).
    Verified against all 72 played group-stage rows.
  * ESPN stamps kickoff in UTC; a late North-American match (e.g. 02:00Z) is
    the previous local day. We convert to a North-American reference offset so
    the date matches martj42's local-date convention.
  * Dedup is by unordered team pair within a date tolerance, so a home/away
    swap or a one-day date representation difference still collapses the
    override onto martj42's authoritative row.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pandas as pd
import requests

from .worldcup import GROUPS_2026, HOST_NATIONS

ESPN_SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard"
)

# 2026 World Cup window: group-stage opener (Jun 11) through the final (Jul 19).
WC_START = date(2026, 6, 11)
WC_END = date(2026, 7, 19)

# North-American reference offset for converting ESPN's UTC kickoff stamp to the
# local calendar date martj42 files the match under. Every 2026 venue sits
# between UTC-7 and UTC-4; US Eastern (UTC-4 in June/July) reproduces martj42's
# date for every match played so far.
_LOCAL_TZ = timezone(timedelta(hours=-4))

# ESPN display names that differ from martj42 / GROUPS_2026 spellings. The other
# 43 participants match exactly.
ESPN_TEAM_NAMES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Czechia": "Czech Republic",
    "Curaçao": "Curacao",   # Curaçao
    "Congo DR": "DR Congo",
    "Türkiye": "Turkey",    # Türkiye
}

# Column order matching the DataFrame returned by data.load_all().
_COLUMNS = [
    "date", "home_team", "away_team", "home_score", "away_score",
    "tournament", "city", "country", "neutral", "shootout_winner",
]

_WC_TEAMS = {t for teams in GROUPS_2026.values() for t in teams}


def _normalize(name: str) -> str:
    return ESPN_TEAM_NAMES.get(name, name)


def _as_int(value) -> int | None:
    """Coerce an ESPN score field (str or number) to int, or None if blank."""
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _local_date(iso_utc: str) -> pd.Timestamp:
    """Convert an ESPN UTC kickoff stamp to the local match date as a Timestamp."""
    dt = datetime.fromisoformat(iso_utc.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return pd.Timestamp(dt.astimezone(_LOCAL_TZ).date())


def parse_event(event: dict) -> dict | None:
    """Parse one ESPN scoreboard event into a match row, or None to skip it.

    Skips events that aren't finished, aren't between two 2026 WC participants,
    or are missing a score. Returned dict matches load_all()'s row schema.
    """
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    comp = competitions[0]

    status = comp.get("status") or event.get("status") or {}
    stype = status.get("type") or {}
    if not stype.get("completed"):
        return None

    home = away = None
    for c in comp.get("competitors") or []:
        team = c.get("team") or {}
        info = {
            "team": _normalize(team.get("displayName", "")),
            "score": _as_int(c.get("score")),
            "shootout": _as_int(c.get("shootoutScore")),
        }
        side = c.get("homeAway")
        if side == "home":
            home = info
        elif side == "away":
            away = info

    if not home or not away:
        return None
    if home["score"] is None or away["score"] is None:
        return None
    # Both sides must be 2026 WC teams; an unmapped ESPN name lands here and is
    # skipped rather than silently creating a phantom team in the ratings.
    if home["team"] not in _WC_TEAMS or away["team"] not in _WC_TEAMS:
        return None

    # Penalty shootout (knockout stage only): regulation/ET score is level and
    # both shootout tallies are present. martj42 records the level score in
    # results.csv and the winner in shootouts.csv.
    shootout_winner = None
    if (
        home["score"] == away["score"]
        and home["shootout"] is not None
        and away["shootout"] is not None
    ):
        shootout_winner = (
            home["team"] if home["shootout"] > away["shootout"] else away["team"]
        )

    return {
        "date": _local_date(event["date"]),
        "home_team": home["team"],
        "away_team": away["team"],
        "home_score": home["score"],
        "away_score": away["score"],
        "tournament": "FIFA World Cup",
        "city": None,
        "country": None,
        "neutral": home["team"] not in HOST_NATIONS,
        "shootout_winner": shootout_winner,
    }


def fetch_finished_matches(
    today: date | None = None,
    lookback_days: int = 6,
    session: requests.Session | None = None,
) -> pd.DataFrame:
    """Fetch finished 2026 World Cup matches from ESPN as load_all()-shaped rows.

    Queries one ESPN scoreboard request per day from
    ``max(WC_START, today - lookback_days)`` through ``min(WC_END, today)``.
    The lookback window keeps each run cheap (a handful of requests) while still
    covering martj42 stalls far longer than its observed <1-day lag. Returns an
    empty frame outside the tournament window.
    """
    if today is None:
        today = datetime.now(timezone.utc).astimezone(_LOCAL_TZ).date()

    start = max(WC_START, today - timedelta(days=lookback_days))
    last = min(WC_END, today)

    owns_session = session is None
    session = session or requests.Session()
    rows: list[dict] = []
    seen: set[tuple] = set()
    try:
        day = start
        while day <= last:
            try:
                resp = session.get(
                    ESPN_SCOREBOARD,
                    params={"dates": day.strftime("%Y%m%d")},
                    headers={"Cache-Control": "no-cache"},
                    timeout=30,
                )
                resp.raise_for_status()
                events = resp.json().get("events", [])
            except (requests.RequestException, ValueError):
                # One bad day shouldn't sink the rest of the window.
                day += timedelta(days=1)
                continue
            for event in events:
                row = parse_event(event)
                if row is None:
                    continue
                key = (frozenset((row["home_team"], row["away_team"])), row["date"])
                if key in seen:
                    continue
                seen.add(key)
                rows.append(row)
            day += timedelta(days=1)
    finally:
        if owns_session:
            session.close()

    return pd.DataFrame(rows, columns=_COLUMNS)


def merge_overrides(
    matches: pd.DataFrame, overrides: pd.DataFrame, tol_days: int = 2
) -> pd.DataFrame:
    """Append override rows that martj42 doesn't already cover, then re-sort.

    A given pair of teams meets at most once within any ``tol_days`` window, so
    matching on the unordered pair within the tolerance reliably identifies the
    same fixture even if home/away order or the exact date differ. martj42's row
    always wins; the override is only kept when no canonical row matches.
    """
    if overrides is None or overrides.empty:
        return matches

    # Only fixtures inside the tournament window can collide with an override.
    window = matches[matches["date"] >= pd.Timestamp(WC_START)]
    existing: dict[frozenset, list[pd.Timestamp]] = {}
    for _, r in window.iterrows():
        existing.setdefault(
            frozenset((r["home_team"], r["away_team"])), []
        ).append(r["date"])

    keep = []
    for _, o in overrides.iterrows():
        pair = frozenset((o["home_team"], o["away_team"]))
        dates = existing.get(pair, [])
        if any(abs((o["date"] - d).days) <= tol_days for d in dates):
            continue  # martj42 already has this fixture
        keep.append(o)

    if not keep:
        return matches

    combined = pd.concat(
        [matches, pd.DataFrame(keep, columns=matches.columns)], ignore_index=True
    )
    return combined.sort_values("date", kind="stable").reset_index(drop=True)


def apply_espn_overrides(
    matches: pd.DataFrame, lookback_days: int = 6
) -> pd.DataFrame:
    """Fetch ESPN finals and merge them into ``matches`` for the export pipeline.

    Wrapped so any ESPN failure degrades gracefully to martj42-only data: the
    daily ratings job must never break because an undocumented endpoint hiccuped.
    """
    try:
        overrides = fetch_finished_matches(lookback_days=lookback_days)
    except Exception as exc:  # noqa: BLE001 - never let ESPN break the pipeline
        print(f"  [espn] skipped (fetch failed: {exc})")
        return matches

    merged = merge_overrides(matches, overrides)
    added = len(merged) - len(matches)
    print(
        f"  [espn] {len(overrides)} finished WC matches fetched, "
        f"{added} ahead of martj42"
    )
    return merged
