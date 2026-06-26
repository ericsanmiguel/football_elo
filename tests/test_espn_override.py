"""Tests for the ESPN live World Cup result override.

These cover the two pure pieces of logic -- parsing a scoreboard event into a
martj42-shaped row, and merging override rows without double-counting what
martj42 already publishes -- without touching the network.
"""

import pandas as pd

from football_elo.espn_override import merge_overrides, parse_event


def _event(home, away, hs, as_, *, completed=True, iso="2026-06-20T17:00Z",
           home_pens=None, away_pens=None):
    """Build a minimal ESPN scoreboard event dict."""
    state = "post" if completed else "in"
    return {
        "date": iso,
        "competitions": [{
            "status": {"type": {"completed": completed, "state": state}},
            "competitors": [
                {"homeAway": "home", "score": hs, "shootoutScore": home_pens,
                 "team": {"displayName": home}},
                {"homeAway": "away", "score": as_, "shootoutScore": away_pens,
                 "team": {"displayName": away}},
            ],
        }],
    }


def test_parse_maps_names_and_sets_neutral_for_host_home():
    # ESPN spellings differ; host (United States) at home => non-neutral.
    row = parse_event(_event("United States", "Türkiye", "2", "1"))
    assert row["home_team"] == "United States"
    assert row["away_team"] == "Turkey"          # Türkiye -> Turkey
    assert row["home_score"] == 2 and row["away_score"] == 1
    assert row["tournament"] == "FIFA World Cup"
    assert row["neutral"] is False               # host home team
    assert row["shootout_winner"] is None


def test_parse_neutral_when_no_host():
    row = parse_event(_event("Germany", "Curaçao", "7", "1"))
    assert row["home_team"] == "Germany"
    assert row["away_team"] == "Curacao"         # Curaçao -> Curacao
    assert row["neutral"] is True                # neither side is a host


def test_parse_remaps_remaining_spellings():
    row = parse_event(_event("Bosnia-Herzegovina", "Czechia", "1", "0"))
    assert row["home_team"] == "Bosnia and Herzegovina"
    assert row["away_team"] == "Czech Republic"


def test_parse_late_utc_kickoff_rolls_back_to_local_date():
    # 02:00Z on Jun 26 is a Jun 25 evening match in North America.
    row = parse_event(_event("United States", "Türkiye", "2", "1",
                             iso="2026-06-26T02:00Z"))
    assert str(row["date"].date()) == "2026-06-25"


def test_parse_skips_unfinished():
    assert parse_event(_event("Spain", "Uruguay", None, None, completed=False)) is None


def test_parse_skips_non_wc_team():
    # An unmapped / non-participant name must not create a phantom team.
    assert parse_event(_event("Narnia", "Spain", "1", "0")) is None


def test_parse_shootout_winner():
    # Level after ET, decided on penalties -> winner recorded, level score kept.
    row = parse_event(_event("Brazil", "England", "1", "1",
                             iso="2026-07-05T19:00Z", home_pens="4", away_pens="3"))
    assert row["home_score"] == 1 and row["away_score"] == 1
    assert row["shootout_winner"] == "Brazil"


def _matches(rows):
    cols = ["date", "home_team", "away_team", "home_score", "away_score",
            "tournament", "city", "country", "neutral", "shootout_winner"]
    return pd.DataFrame(rows, columns=cols)


def _override_row(home, away, hs, as_, d):
    return {
        "date": pd.Timestamp(d), "home_team": home, "away_team": away,
        "home_score": hs, "away_score": as_, "tournament": "FIFA World Cup",
        "city": None, "country": None, "neutral": True, "shootout_winner": None,
    }


def test_merge_adds_new_match():
    base = _matches([_override_row("Spain", "Uruguay", 4, 0, "2026-06-21")])
    overrides = _matches([_override_row("Egypt", "Iran", 3, 0, "2026-06-26")])
    merged = merge_overrides(base, overrides)
    assert len(merged) == 2
    assert ((merged["home_team"] == "Egypt") & (merged["away_team"] == "Iran")).any()


def test_merge_dedupes_against_martj42_even_with_swap_and_date_drift():
    # martj42 already has the fixture (home/away swapped, date off by a day).
    base = _matches([_override_row("Iran", "Egypt", 0, 3, "2026-06-26")])
    overrides = _matches([_override_row("Egypt", "Iran", 3, 0, "2026-06-27")])
    merged = merge_overrides(base, overrides)
    assert len(merged) == 1          # override dropped, martj42 row wins
    assert merged.iloc[0]["home_team"] == "Iran"


def test_merge_keeps_chronological_order():
    base = _matches([_override_row("Spain", "Uruguay", 4, 0, "2026-06-21")])
    overrides = _matches([_override_row("Egypt", "Iran", 3, 0, "2026-06-15")])
    merged = merge_overrides(base, overrides)
    assert list(merged["date"]) == sorted(merged["date"])
