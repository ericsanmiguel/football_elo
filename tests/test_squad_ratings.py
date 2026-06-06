"""Unit tests for position-by-position player and team ratings."""

import pandas as pd
import pytest

from football_elo.squad_strength import (
    GROUP_ORDER,
    player_position_ratings,
    position_group,
    team_position_scores,
)


def _squad(rows):
    """Build a squad DataFrame from (team, code, age, value) tuples."""
    return pd.DataFrame(
        [
            {"team": t, "player": f"{t}-{i}", "position_code": c,
             "age_at_kickoff": a, "value_at_kickoff": v}
            for i, (t, c, a, v) in enumerate(rows)
        ]
    )


class TestPositionGroup:
    def test_mapping(self):
        assert position_group("GK") == "GK"
        assert position_group("DF") == "DEF"
        assert position_group("MF") == "MID"
        assert position_group("FW") == "FWD"

    def test_case_and_whitespace(self):
        assert position_group(" fw ") == "FWD"

    def test_unknown(self):
        assert position_group("XX") is None
        assert position_group(None) is None


class TestPlayerRatings:
    def test_within_bounds(self):
        # A wide value spread including an extreme outlier stays clamped to [0,100].
        rows = [("A", "FW", 25, v) for v in (1e5, 1e6, 1e7, 5e7, 3e8)]
        df = player_position_ratings(_squad(rows))
        assert df["rating"].between(0, 100).all()

    def test_monotonic_within_position(self):
        # Same age, increasing value -> non-decreasing rating within a position.
        rows = [("A", "MF", 26, v) for v in (1e6, 5e6, 2e7, 8e7)]
        df = player_position_ratings(_squad(rows))
        ratings = list(df.sort_values("value_at_kickoff")["rating"])
        assert all(ratings[i] <= ratings[i + 1] for i in range(len(ratings) - 1))

    def test_normalized_per_position(self):
        # A goalkeeper and a forward with identical value are each judged against
        # their own group, so a lone GK and a lone FW both land at the group mean.
        rows = [("A", "GK", 27, 2e7), ("A", "FW", 27, 2e7),
                ("B", "GK", 27, 4e6), ("B", "FW", 27, 4e6)]
        df = player_position_ratings(_squad(rows))
        gk = df[df["pgroup"] == "GK"].sort_values("value_at_kickoff")["rating"].tolist()
        fw = df[df["pgroup"] == "FWD"].sort_values("value_at_kickoff")["rating"].tolist()
        # Same value ordering within each group -> same rating pattern across groups.
        assert gk == fw

    def test_unknown_position_left_nan(self):
        df = player_position_ratings(_squad([("A", "XX", 25, 1e6)]))
        assert df["pgroup"].isna().all()
        assert df["rating"].isna().all()


class TestTeamPositionScores:
    def test_scores_within_bounds_and_overall(self):
        rows = []
        for team, base in [("A", 5e7), ("B", 2e7), ("C", 5e6)]:
            for code in ("GK", "DF", "MF", "FW"):
                rows += [(team, code, 26, base), (team, code, 28, base * 0.6)]
        scores = team_position_scores(player_position_ratings(_squad(rows)))
        for team in ("A", "B", "C"):
            for g in GROUP_ORDER:
                assert 0 <= scores[team][g] <= 100
            assert scores[team]["overall"] == pytest.approx(
                sum(scores[team][g] for g in GROUP_ORDER) / 4, abs=0.1
            )

    def test_stronger_unit_scores_higher(self):
        # Team A has far more valuable defenders than team B.
        rows = [("A", "DF", 26, 8e7), ("A", "DF", 26, 7e7),
                ("B", "DF", 26, 3e6), ("B", "DF", 26, 2e6)]
        scores = team_position_scores(player_position_ratings(_squad(rows)))
        assert scores["A"]["DEF"] > scores["B"]["DEF"]
