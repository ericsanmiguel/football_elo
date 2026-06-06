"""Aggregate per-player adjusted values into a per-team squad score."""

from __future__ import annotations

import math
from pathlib import Path

import pandas as pd

from .player_strength import adjusted_value


def _player_score(v: float, a: float,
                  tm_curve: dict[int, float] | None,
                  use_log: bool) -> float:
    """Age-adjusted TM value, optionally log-transformed.

    log1p(value_in_millions) applies a concave transform so that the gap
    between an amateur (~€0) and a pro (€5-10M) is larger than between a pro
    and a superstar (€100M). Captures diminishing marginal returns on
    player quality.
    """
    adj = adjusted_value(v, a, tm_curve)
    if math.isnan(adj):
        return float('nan')
    if use_log:
        return math.log1p(max(0.0, adj) / 1e6)  # log(1 + millions)
    return adj


def squad_score_for_team(team_rows: pd.DataFrame,
                         tm_curve: dict[int, float] | None = None,
                         agg: str = "mean",
                         use_log: bool = True) -> float:
    """Per-squad aggregate of age-adjusted player values.

    use_log=True applies log1p to each player's value (in millions) before
    aggregating — reflects diminishing returns on player worth.
    agg='mean' averages across matched players; 'sum' totals them.
    """
    vals: list[float] = []
    for _, r in team_rows.iterrows():
        v = r.get('value_at_kickoff')
        a = r.get('age_at_kickoff')
        if pd.isna(v) or pd.isna(a):
            continue
        score = _player_score(float(v), float(a), tm_curve, use_log)
        if not math.isnan(score):
            vals.append(score)
    if not vals:
        return 0.0
    if agg == "mean":
        return sum(vals) / len(vals)
    return sum(vals)


def squad_scores(squad_df: pd.DataFrame,
                 tm_curve: dict[int, float] | None = None,
                 agg: str = "mean",
                 use_log: bool = True) -> dict[str, float]:
    """Return {team: score} from a squad DataFrame for a single tournament."""
    return {
        team: squad_score_for_team(rows, tm_curve, agg=agg, use_log=use_log)
        for team, rows in squad_df.groupby('team')
    }


def z_scores(scores: dict[str, float]) -> dict[str, float]:
    """Z-normalize scores across the tournament's teams."""
    vals = list(scores.values())
    if not vals:
        return {}
    mu = sum(vals) / len(vals)
    var = sum((v - mu) ** 2 for v in vals) / len(vals)
    sd = var ** 0.5
    if sd == 0:
        return {t: 0.0 for t in scores}
    return {t: (v - mu) / sd for t, v in scores.items()}


def load_tournament_squads(year: int) -> pd.DataFrame:
    """Load data/squads/{year}.csv."""
    root = Path(__file__).resolve().parent.parent.parent
    path = root / "data" / "squads" / f"{year}.csv"
    return pd.read_csv(path)


# ---------------------------------------------------------------------------
# Position-by-position player and team-unit ratings (display feature).
#
# Same age-adjust + log methodology as the team squad index, but normalized
# *within position group* so a goalkeeper is rated against other goalkeepers,
# not against forwards (whose Transfermarkt values run systematically higher).
# A z-score is mapped to a FIFA-like 0-100 scale: rating = clamp(50 + K*z).
# ---------------------------------------------------------------------------

# Transfermarkt position_code -> display position group.
POSITION_GROUPS = {"GK": "GK", "DF": "DEF", "MF": "MID", "FW": "FWD"}
GROUP_ORDER = ["GK", "DEF", "MID", "FWD"]

# Spread of the 0-100 scale: a +1 SD player scores 50 + K. ~18 keeps the bulk of
# players in roughly 30-95 with the endpoints (0/100) reserved for true outliers.
PLAYER_RATING_K = 18.0


def position_group(position_code: object) -> str | None:
    """Map a Transfermarkt position code (GK/DF/MF/FW) to a display group."""
    return POSITION_GROUPS.get(str(position_code).strip().upper())


def _clip(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _rating_from_scores(scores: dict[object, float], k: float) -> dict[object, float]:
    """z-normalize a {key: score} map and rescale to clamp(50 + k*z, 0, 100)."""
    vals = [v for v in scores.values() if not math.isnan(v)]
    if not vals:
        return {}
    mu = sum(vals) / len(vals)
    sd = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
    out = {}
    for key, v in scores.items():
        if math.isnan(v):
            continue
        z = 0.0 if sd == 0 else (v - mu) / sd
        out[key] = round(_clip(50.0 + k * z), 1)
    return out


def player_position_ratings(
    squad_df: pd.DataFrame, tm_curve: dict[int, float] | None = None,
    k: float = PLAYER_RATING_K,
) -> pd.DataFrame:
    """Add ``pgroup``, ``pscore`` and ``rating`` (0-100) columns to a squad frame.

    ``pscore`` is the log-transformed age-adjusted value (the same per-player
    score the team index aggregates). ``rating`` z-normalizes ``pscore`` within
    each position group across all teams' players, then maps it to 0-100.
    """
    df = squad_df.copy()
    df["pgroup"] = df["position_code"].map(position_group)
    df["pscore"] = [
        _player_score(float(v), float(a), tm_curve, True)
        if pd.notna(v) and pd.notna(a) else float("nan")
        for v, a in zip(df["value_at_kickoff"], df["age_at_kickoff"])
    ]
    df["rating"] = float("nan")
    for group in GROUP_ORDER:
        idx = df.index[df["pgroup"] == group]
        scores = {i: df.at[i, "pscore"] for i in idx}
        for i, rating in _rating_from_scores(scores, k).items():
            df.at[i, "rating"] = rating
    return df


def team_position_scores(
    rated_df: pd.DataFrame, k: float = PLAYER_RATING_K,
) -> dict[str, dict[str, float]]:
    """Per-team GK/DEF/MID/FWD scores (0-100), plus an ``overall`` average.

    For each position group, a team's mean ``pscore`` is z-normalized across the
    48 teams and mapped to 0-100 — i.e. how strong that team's unit is relative
    to the other teams' units in the same position.
    """
    out: dict[str, dict[str, float]] = {t: {} for t in rated_df["team"].unique()}
    for group in GROUP_ORDER:
        sub = rated_df[rated_df["pgroup"] == group]
        team_means: dict[str, float] = {}
        for team, rows in sub.groupby("team"):
            vals = [v for v in rows["pscore"] if not (isinstance(v, float) and math.isnan(v))]
            if vals:
                team_means[team] = sum(vals) / len(vals)
        for team, rating in _rating_from_scores(team_means, k).items():
            out[team][group] = rating
    for team, scores in out.items():
        present = [scores[g] for g in GROUP_ORDER if g in scores]
        if present:
            scores["overall"] = round(sum(present) / len(present), 1)
    return out
