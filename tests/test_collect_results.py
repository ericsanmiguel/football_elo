"""Tests for collect_results' knockout parsing, especially the shootout fallback.

A knockout match can only end level if it was decided on penalties, so a level
score with no recorded shootout winner means the result isn't in our data yet
(e.g. ESPN flagged the match complete before publishing the shootout). Such a
match must be skipped -- treated as undecided -- rather than silently advancing
the home team, which would pin the wrong side into the simulated bracket.
"""

from football_elo.worldcup import collect_results


class _Elo:
    """Minimal stand-in for EloSystem: collect_results only reads .history."""

    def __init__(self, history):
        self.history = history


def _rec(team, opp, ts, os_, *, date, shootout=None, is_home=True):
    return {
        "date": date, "team": team, "opponent": opp,
        "team_score": ts, "opponent_score": os_,
        "shootout_winner": shootout,
        "tournament": "FIFA World Cup", "is_home": is_home,
    }


def _knockout(history):
    return collect_results(_Elo(history))[1]


def test_level_score_with_shootout_winner_is_recorded():
    history = [_rec("Brazil", "France", 1, 1, date="2026-06-29",
                    shootout="France")]
    ko = _knockout(history)
    assert len(ko) == 1
    assert ko[0]["winner"] == "France"
    assert ko[0]["pens"] is True
    assert ko[0]["score"] == [1, 1]


def test_level_score_without_shootout_winner_is_skipped():
    # Completed-but-undecided: must NOT default to the home team.
    history = [_rec("Spain", "Portugal", 0, 0, date="2026-06-29",
                    shootout=None)]
    assert _knockout(history) == []


def test_level_score_with_invalid_shootout_winner_is_skipped():
    # A shootout name that isn't one of the two teams is treated as missing.
    history = [_rec("Spain", "Portugal", 2, 2, date="2026-06-29",
                    shootout="Italy")]
    assert _knockout(history) == []


def test_decisive_score_ignores_shootout_field():
    history = [_rec("Argentina", "England", 2, 1, date="2026-06-29",
                    shootout="England")]  # stray shootout value must be ignored
    ko = _knockout(history)
    assert len(ko) == 1
    assert ko[0]["winner"] == "Argentina"
    assert ko[0]["pens"] is False


def test_decisive_away_win():
    history = [_rec("Argentina", "England", 0, 3, date="2026-06-29")]
    ko = _knockout(history)
    assert len(ko) == 1 and ko[0]["winner"] == "England"


def test_group_match_lands_in_group_results_not_knockout():
    # Mexico (A0) vs South Korea (A2), before KNOCKOUT_START.
    history = [_rec("Mexico", "South Korea", 2, 1, date="2026-06-15")]
    group_results, knockout_results, _ = collect_results(_Elo(history))
    assert knockout_results == []
    assert group_results["A"][(0, 2)] == (2, 1)
