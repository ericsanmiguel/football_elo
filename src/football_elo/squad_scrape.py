"""Scrape official 26-man World Cup 2026 squads from Transfermarkt.

One-off / manual data acquisition (run via ``python -m football_elo scrape-squads``),
not part of the daily GitHub Action — tournament squads are static once announced.

Per nation we read three Transfermarkt views and join them on the stable player id:

* ``leistungsdaten/.../reldata/FIWC&2025`` — the *authoritative tournament squad*
  (exactly the registered 23-26), giving player id, name, position group and shirt
  number, but no market value or club.
* ``kader/...`` (current squad view) — the national-team pool, which carries the
  current market value, club and date of birth for the players TM already lists
  there. We deliberately omit ``saison_id`` because the season-pinned view returns
  stale season-start valuations for players whose value moved recently.
* the player profile page — fallback for squad members not yet on the pool page
  (new call-ups TM hasn't folded into the curated national squad).

The output schema matches ``data/squads/{2018,2022}.csv`` plus a new ``club`` column:
``team,player,position_code,club,shirt_number,player_id,date_of_birth,age_at_kickoff,value_at_kickoff``.
"""

from __future__ import annotations

import datetime
import re
import time
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .worldcup import GROUPS_2026

BASE = "https://www.transfermarkt.com"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

# 2026 World Cup tournament coordinates on Transfermarkt.
COMPETITION = "FIWC"          # FIFA World Cup competition id
RELDATA = "FIWC%262025"      # reldata/<competition>&<season>, %26 == '&'
KICKOFF = datetime.date(2026, 6, 11)

# Transfermarkt number-cell background class -> position code (matches 2018/2022).
_BG_TO_CODE = {
    "bg_Torwart": "GK",
    "bg_Abwehr": "DF",
    "bg_Mittelfeld": "MF",
    "bg_Sturm": "FW",
}

# Transfermarkt English nation names that differ from our canonical GROUPS_2026 keys.
_NAME_OVERRIDES = {
    "Bosnia-Herzegovina": "Bosnia and Herzegovina",
    "Czechia": "Czech Republic",
    "Curaçao": "Curacao",
    "Democratic Republic of the Congo": "DR Congo",
    "Turkiye": "Turkey",
}

_CANON = {t for teams in GROUPS_2026.values() for t in teams}


class _Fetcher:
    """Session wrapper with polite throttling and retry/backoff on TM's 502/504s."""

    def __init__(self, delay: float = 1.2):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.delay = delay

    def get(self, url: str) -> str | None:
        for attempt in range(5):
            try:
                r = self.session.get(url, timeout=30)
                if r.status_code == 200:
                    time.sleep(self.delay)
                    return r.content.decode("utf-8", "replace")
            except requests.RequestException:
                pass
            time.sleep(self.delay + 1.5 * attempt)
        return None


def _parse_value(text: str | None) -> float | None:
    """Parse a Transfermarkt market value (e.g. '€80.00m', '€500k') into euros."""
    if not text:
        return None
    m = re.search(r"([\d.,]+)\s*(bn|m|k)?", text.replace("\xa0", " "))
    if not m:
        return None
    num = float(m.group(1).replace(",", ""))
    mult = {"bn": 1e9, "m": 1e6, "k": 1e3, None: 1.0}[m.group(2)]
    value = num * mult
    return value if value > 0 else None


def _parse_dob(text: str | None) -> datetime.date | None:
    """Parse a dd/mm/yyyy date string."""
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", text or "")
    if not m:
        return None
    day, month, year = (int(x) for x in m.groups())
    try:
        return datetime.date(year, month, day)
    except ValueError:
        return None


def _age_at_kickoff(dob: datetime.date | None) -> float | None:
    return round((KICKOFF - dob).days / 365.25, 2) if dob else None


def _position_code(row) -> str | None:
    cell = row.select_one("td.rueckennummer")
    for cls in (cell.get("class") or []) if cell else []:
        if cls in _BG_TO_CODE:
            return _BG_TO_CODE[cls]
    return None


def fetch_nations(fetch: _Fetcher) -> list[tuple[str, str, str]]:
    """Return [(canonical_team, tm_slug, verein_id)] for the 48 participants.

    Discovered live from the tournament participants page so we don't hard-code
    Transfermarkt club ids. Validated against GROUPS_2026.
    """
    url = f"{BASE}/weltmeisterschaft-2026/teilnehmer/pokalwettbewerb/{COMPETITION}"
    html = fetch.get(url)
    if not html:
        raise RuntimeError("Could not load the World Cup 2026 participants page")
    soup = BeautifulSoup(html, "lxml")
    table = soup.select("table.items")[0]  # first items table = participants
    found: dict[tuple[str, str], str] = {}
    for a in table.select('a[href*="/startseite/verein/"]'):
        m = re.search(r"/([a-z0-9\-]+)/startseite/verein/(\d+)", a["href"])
        name = (a.get("title") or a.get_text(strip=True)).strip()
        if m and name:
            found[(m.group(1), m.group(2))] = name

    nations: list[tuple[str, str, str]] = []
    for (slug, vid), tm_name in found.items():
        team = _NAME_OVERRIDES.get(tm_name, tm_name)
        if team in _CANON:
            nations.append((team, slug, vid))

    teams = {n[0] for n in nations}
    missing = _CANON - teams
    if missing:
        raise RuntimeError(f"Participants page missing {len(missing)} teams: {sorted(missing)}")
    # De-duplicate (one row per team) and order by GROUPS_2026.
    by_team = {n[0]: n for n in nations}
    return [by_team[t] for t in sorted(_CANON)]


def _parse_squad_table(html: str | None) -> dict[str, dict]:
    """Parse a kader/leistungsdaten squad table into {player_id: fields}."""
    out: dict[str, dict] = {}
    if not html:
        return out
    soup = BeautifulSoup(html, "lxml")
    for row in soup.select("table.items > tbody > tr"):
        link = row.select_one('a[href*="/profil/spieler/"]')
        if not link:
            continue
        pid = re.search(r"/profil/spieler/(\d+)", link["href"]).group(1)
        if pid in out:
            continue
        inline = row.select_one("table.inline-table")
        rows = inline.find_all("tr") if inline else []
        position = rows[1].get_text(strip=True) if len(rows) > 1 else ""
        dob = None
        for td in row.select("td.zentriert"):
            dob = _parse_dob(td.get_text())
            if dob:
                break
        club_img = row.select_one('a[href*="/startseite/verein/"] img[title]')
        value_cell = row.select_one("td.rechts.hauptlink")
        shirt = row.select_one("td.rueckennummer")
        out[pid] = {
            "player_id": pid,
            "href": link["href"],
            "player": link.get_text(strip=True),
            "position_code": _position_code(row),
            "position": position,
            "date_of_birth": dob,
            "club": club_img.get("title") if club_img else None,
            "value_at_kickoff": _parse_value(value_cell.get_text() if value_cell else None),
            "shirt_number": shirt.get_text(strip=True) if shirt else "",
        }
    return out


def _profile_details(fetch: _Fetcher, href: str) -> tuple[str | None, float | None, datetime.date | None]:
    """Return (club, market_value, dob) from a player's profile page."""
    html = fetch.get(f"{BASE}{href}")
    if not html:
        return None, None, None
    soup = BeautifulSoup(html, "lxml")
    mv = soup.select_one(".data-header__market-value-wrapper")
    club = soup.select_one(".data-header__club a")
    birth = soup.select_one("[itemprop=birthDate]")
    return (
        club.get_text(strip=True) if club else None,
        _parse_value(mv.get_text()) if mv else None,
        _parse_dob(birth.get_text()) if birth else None,
    )


def _dedupe_by_shirt(rows: list[dict], team: str) -> list[dict]:
    """Resolve shirt-number collisions left by pre-tournament squad replacements.

    Transfermarkt's tournament page lists both a withdrawn player and his
    replacement, which collide on the same shirt number. The active squad member
    is the one Transfermarkt keeps in the current national pool; break any
    remaining tie by market value. Players with a unique (or blank) number are
    always kept — pool-absence alone never drops a player (new call-ups are
    frequently not yet in the pool).
    """
    by_shirt: dict[str, list[dict]] = {}
    kept: list[dict] = []
    for r in rows:
        shirt = r["shirt_number"]
        if shirt:
            by_shirt.setdefault(shirt, []).append(r)
        else:
            kept.append(r)
    for shirt, group in by_shirt.items():
        if len(group) == 1:
            kept.append(group[0])
            continue
        group.sort(key=lambda r: (0 if r["_in_pool"] else 1, -(r["value_at_kickoff"] or 0)))
        best, dropped = group[0], group[1:]
        kept.append(best)
        names = ", ".join(d["player"] for d in dropped)
        print(f"      {team}: #{shirt} kept {best['player']}, dropped {names} (replaced)")
    return kept


def scrape_nation(fetch: _Fetcher, team: str, slug: str, vid: str) -> list[dict]:
    """Scrape one nation's official tournament squad."""
    squad = _parse_squad_table(
        fetch.get(f"{BASE}/{slug}/leistungsdaten/verein/{vid}/reldata/{RELDATA}/plus/1")
    )
    # No saison_id: TM serves the *current* squad with current market values.
    # The season-pinned view returns stale season-start valuations for players
    # whose value moved recently (e.g. rising youngsters), so we avoid it and
    # let the profile-page fallback cover squad members not in the current pool.
    pool = _parse_squad_table(
        fetch.get(f"{BASE}/{slug}/kader/verein/{vid}/plus/1")
    )
    rows: list[dict] = []
    for pid, p in squad.items():
        ref = pool.get(pid)
        club, value, dob = (
            (ref["club"], ref["value_at_kickoff"], ref["date_of_birth"])
            if ref else (None, None, None)
        )
        if club is None or value is None or dob is None:
            pc, pv, pd_ = _profile_details(fetch, p["href"])
            club = club or pc
            value = value if value is not None else pv
            dob = dob or pd_
        rows.append({
            "team": team,
            "player": p["player"],
            "position_code": p["position_code"] or (ref or {}).get("position_code"),
            "club": club,
            "shirt_number": p["shirt_number"],
            "player_id": pid,
            "date_of_birth": dob.isoformat() if dob else "",
            "age_at_kickoff": _age_at_kickoff(dob),
            "value_at_kickoff": value,
            "_in_pool": ref is not None,
        })
    rows = _dedupe_by_shirt(rows, team)
    for r in rows:
        del r["_in_pool"]
    return rows


def scrape_squads(year: int = 2026, delay: float = 1.2) -> pd.DataFrame:
    """Scrape all 48 nations' squads into a DataFrame."""
    if year != 2026:
        raise ValueError("scrape_squads currently supports the 2026 World Cup only")
    fetch = _Fetcher(delay=delay)
    nations = fetch_nations(fetch)
    all_rows: list[dict] = []
    for i, (team, slug, vid) in enumerate(nations, 1):
        rows = scrape_nation(fetch, team, slug, vid)
        if not rows:  # transient 502 burst on the squad page — give it one more pass
            time.sleep(5)
            rows = scrape_nation(fetch, team, slug, vid)
        all_rows.extend(rows)
        miss_v = sum(1 for r in rows if not r["value_at_kickoff"])
        flag = "  <-- check" if len(rows) < 23 or miss_v else ""
        print(f"  [{i:2}/48] {team:24} {len(rows):2} players "
              f"(missing value: {miss_v}){flag}")
    return pd.DataFrame(all_rows)


def write_squads(year: int = 2026, delay: float = 1.2) -> Path:
    """Scrape and write data/squads/{year}.csv."""
    df = scrape_squads(year=year, delay=delay)
    root = Path(__file__).resolve().parent.parent.parent
    path = root / "data" / "squads" / f"{year}.csv"
    df.to_csv(path, index=False)
    print(f"\nWrote {len(df)} players across {df['team'].nunique()} teams to {path}")
    return path
