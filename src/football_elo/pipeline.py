"""EloSystem: orchestrates Elo computation over a match dataset."""

import pandas as pd

from .config import HOME_ADVANTAGE, INITIAL_RATING
from .elo import compute_rating_change, expected_result, match_result_value
from .tournaments import get_k_factor


class EloSystem:
    """Processes matches chronologically and maintains Elo ratings."""

    def __init__(
        self,
        initial_rating: float = INITIAL_RATING,
        home_advantage: float = HOME_ADVANTAGE,
        snapshots: list[dict] | None = None,
    ):
        self.initial_rating = initial_rating
        self.home_advantage = home_advantage
        self.ratings: dict[str, float] = {}
        self.history: list[dict] = []
        # Optional pre-match snapshot sink. Used by calibrate_poisson.py to
        # collect (R_home_pre, R_away_pre, goals, ...) tuples without
        # rerunning Elo from scratch.
        self.snapshots = snapshots

    def get_rating(self, team: str) -> float:
        return self.ratings.get(team, self.initial_rating)

    def process_match(self, row: pd.Series) -> None:
        home = row["home_team"]
        away = row["away_team"]
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        is_neutral = bool(row["neutral"])
        tournament = row["tournament"]
        shootout_winner = row.get("shootout_winner")
        if pd.isna(shootout_winner):
            shootout_winner = None

        k = get_k_factor(tournament)
        r_home = self.get_rating(home)
        r_away = self.get_rating(away)

        delta_home, delta_away = compute_rating_change(
            r_home, r_away, home_score, away_score,
            k_factor=k, is_neutral=is_neutral,
            shootout_winner=shootout_winner,
            home_team=home, away_team=away,
        )

        # Compute expected and actual for history
        ha = 0.0 if is_neutral else self.home_advantage
        we_home = expected_result(r_home + ha, r_away)
        w_home, w_away = match_result_value(
            home_score, away_score, shootout_winner, home, away
        )

        new_home = r_home + delta_home
        new_away = r_away + delta_away

        date = row["date"]

        if self.snapshots is not None:
            self.snapshots.append({
                "date": date,
                "home_team": home, "away_team": away,
                "r_home_pre": r_home, "r_away_pre": r_away,
                "is_neutral": is_neutral,
                "home_score": home_score, "away_score": away_score,
                "tournament": tournament,
            })

        # Record history for both teams
        self.history.append({
            "date": date, "team": home, "opponent": away,
            "team_score": home_score, "opponent_score": away_score,
            "shootout_winner": shootout_winner,
            "tournament": tournament, "k_factor": k,
            "rating_before": round(r_home, 2),
            "rating_after": round(new_home, 2),
            "rating_change": round(delta_home, 2),
            "expected": round(we_home, 4),
            "actual": w_home, "is_home": True, "is_neutral": is_neutral,
        })
        self.history.append({
            "date": date, "team": away, "opponent": home,
            "team_score": away_score, "opponent_score": home_score,
            "tournament": tournament, "k_factor": k,
            "rating_before": round(r_away, 2),
            "rating_after": round(new_away, 2),
            "rating_change": round(delta_away, 2),
            "expected": round(1.0 - we_home, 4),
            "actual": w_away, "is_home": False, "is_neutral": is_neutral,
        })

        self.ratings[home] = new_home
        self.ratings[away] = new_away

    def process_all(
        self, matches: pd.DataFrame, through_date: str | None = None
    ) -> None:
        if through_date is not None:
            cutoff = pd.Timestamp(through_date)
            matches = matches[matches["date"] < cutoff]
        for _, row in matches.iterrows():
            self.process_match(row)

    def get_current_rankings(self) -> pd.DataFrame:
        rows = [
            {"team": team, "rating": round(rating, 2)}
            for team, rating in self.ratings.items()
        ]
        df = pd.DataFrame(rows).sort_values("rating", ascending=False).reset_index(drop=True)
        df.index += 1
        df.index.name = "rank"
        return df

    def get_team_history(self, team: str) -> pd.DataFrame:
        records = [r for r in self.history if r["team"] == team]
        return pd.DataFrame(records)

    def get_history_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame(self.history)
