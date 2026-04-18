"""Backtest predictions against historical World Cups.

For each completed match in a given WC, compute the model's W/D/L
probability and compare to the actual outcome via multiclass Brier
score and log-loss.

This is a match-level evaluation — it does not simulate the tournament
structure. Tournament-level metrics (e.g. p_winner backtest) would
require reconstructing 2018/2022 brackets and can be added later.
"""

from __future__ import annotations

import argparse
import math
import random
from typing import Callable

import pandas as pd

from .data import download_data, load_all
from .pipeline import EloSystem
from .worldcup import match_probabilities
from .squad_strength import load_tournament_squads, squad_scores, z_scores


WC_METADATA = {
    2018: {"kickoff": "2018-06-14", "end": "2018-07-16"},
    2022: {"kickoff": "2022-11-20", "end": "2022-12-19"},
}


RatingsFn = Callable[[str], float]


def snapshot_ratings(gender: str = "men", through_date: str | None = None) -> dict[str, float]:
    """Reconstruct running Elo ratings by replaying matches up to through_date."""
    download_data(gender=gender)
    matches = load_all(gender=gender)
    elo = EloSystem()
    elo.process_all(matches, through_date=through_date)
    return dict(elo.ratings)


def load_tournament_matches(year: int, gender: str = "men") -> pd.DataFrame:
    """Return the played matches of a given WC, sorted by date."""
    meta = WC_METADATA[year]
    download_data(gender=gender)
    matches = load_all(gender=gender)
    mask = (
        (matches["tournament"] == "FIFA World Cup")
        & (matches["date"] >= pd.Timestamp(meta["kickoff"]))
        & (matches["date"] <= pd.Timestamp(meta["end"]))
    )
    return matches[mask].sort_values("date").reset_index(drop=True)


def _match_scores(prob_home: float, prob_draw: float, prob_away: float,
                  home_score: int, away_score: int) -> tuple[float, float]:
    """Per-match multiclass Brier score and log-loss."""
    if home_score > away_score:
        actual = (1.0, 0.0, 0.0)
        p_actual = prob_home
    elif home_score < away_score:
        actual = (0.0, 0.0, 1.0)
        p_actual = prob_away
    else:
        actual = (0.0, 1.0, 0.0)
        p_actual = prob_draw

    brier = (
        (prob_home - actual[0]) ** 2
        + (prob_draw - actual[1]) ** 2
        + (prob_away - actual[2]) ** 2
    )
    log_loss = -math.log(max(p_actual, 1e-10))
    return brier, log_loss


def _match_probs_with_uncertainty(
    r_home: float, r_away: float, home: str, is_neutral: bool,
    sigma: float, n_samples: int, rng: random.Random,
) -> tuple[float, float, float]:
    """Average match_probabilities over N samples of ratings ~ N(mu, sigma).

    Each team's rating is sampled independently. Returns marginal W/D/L.
    """
    if sigma <= 0:
        return match_probabilities(r_home, r_away, home_team=home, neutral=is_neutral)
    pw = pd_ = pl = 0.0
    for _ in range(n_samples):
        rh = r_home + rng.gauss(0, sigma)
        ra = r_away + rng.gauss(0, sigma)
        h, d, a = match_probabilities(rh, ra, home_team=home, neutral=is_neutral)
        pw += h; pd_ += d; pl += a
    return pw / n_samples, pd_ / n_samples, pl / n_samples


def backtest_worldcup(
    year: int,
    ratings_fn: RatingsFn | None = None,
    gender: str = "men",
    sigma: float = 0.0,
    n_rating_samples: int = 400,
    seed: int = 42,
) -> dict:
    """Score a rating function on a past WC.

    ratings_fn: team_name -> rating. If None, uses pure Elo snapshot at kickoff.
    sigma: std dev of Gaussian rating uncertainty applied per-team per-sample.
           0 disables uncertainty (pure analytical match_probabilities).
    Returns dict with n_matches, mean_brier, mean_log_loss, per_match list.
    """
    meta = WC_METADATA[year]
    if ratings_fn is None:
        ratings = snapshot_ratings(gender=gender, through_date=meta["kickoff"])
        ratings_fn = lambda team: ratings.get(team, 1500.0)

    matches = load_tournament_matches(year, gender=gender)
    rng = random.Random(seed)
    briers: list[float] = []
    losses: list[float] = []
    per_match: list[dict] = []

    for _, row in matches.iterrows():
        home = row["home_team"]
        away = row["away_team"]
        is_neutral = bool(row["neutral"])
        r_home = ratings_fn(home)
        r_away = ratings_fn(away)

        p_home, p_draw, p_away = _match_probs_with_uncertainty(
            r_home, r_away, home, is_neutral, sigma, n_rating_samples, rng
        )

        brier, log_loss = _match_scores(
            p_home, p_draw, p_away,
            int(row["home_score"]), int(row["away_score"]),
        )
        briers.append(brier)
        losses.append(log_loss)
        per_match.append({
            "date": row["date"].strftime("%Y-%m-%d"),
            "home": home, "away": away,
            "score": f"{int(row['home_score'])}-{int(row['away_score'])}",
            "neutral": is_neutral,
            "r_home": round(r_home, 1),
            "r_away": round(r_away, 1),
            "p_home": round(p_home, 3),
            "p_draw": round(p_draw, 3),
            "p_away": round(p_away, 3),
            "brier": round(brier, 4),
            "log_loss": round(log_loss, 4),
        })

    n = len(briers)
    return {
        "year": year,
        "gender": gender,
        "n_matches": n,
        "sigma": sigma,
        "mean_brier": sum(briers) / n if n else float("nan"),
        "mean_log_loss": sum(losses) / n if n else float("nan"),
        "per_match": per_match,
    }


def calibrate_sigma(
    years: list[int] = (2018, 2022),
    gender: str = "men",
    sigmas: list[float] = None,
) -> dict:
    """Grid search rating-uncertainty sigma to minimize pooled Brier."""
    if sigmas is None:
        sigmas = [0, 20, 40, 60, 80, 100, 120, 150, 200]
    results = []
    for s in sigmas:
        row = {"sigma": s}
        total_brier = 0.0
        total_loss = 0.0
        total_n = 0
        for y in years:
            r = backtest_worldcup(y, gender=gender, sigma=s)
            row[f"brier_{y}"] = r["mean_brier"]
            row[f"log_loss_{y}"] = r["mean_log_loss"]
            total_brier += r["mean_brier"] * r["n_matches"]
            total_loss += r["mean_log_loss"] * r["n_matches"]
            total_n += r["n_matches"]
        row["brier_pooled"] = total_brier / total_n
        row["log_loss_pooled"] = total_loss / total_n
        results.append(row)
    best = min(results, key=lambda r: r["brier_pooled"])
    return {"grid": results, "best": best}


TEAM_NAME_MAP_SQUAD_TO_ELO = {
    # jfjelstul / TM side -> martj42 / Elo side
    "Korea Republic": "South Korea",
    "Iran": "Iran",
    "United States": "United States",
    "Ivory Coast": "Ivory Coast",
    "Serbia": "Serbia",
}


def composite_ratings_fn(year: int, gender: str, beta: float) -> tuple[RatingsFn, dict[str, float]]:
    """Build a rating function that blends Elo and squad z-score.

    composite(team) = elo(team) + beta * squad_z(team) * sigma_elo

    where sigma_elo is the std of Elo across the WC's participating teams.
    Returns (ratings_fn, debug_dict with per-team breakdown).
    """
    meta = WC_METADATA[year]
    elo_snapshot = snapshot_ratings(gender=gender, through_date=meta["kickoff"])

    squads = load_tournament_squads(year)
    # Compute per-team squad scores (summed age-adjusted TM values)
    team_scores = squad_scores(squads)
    # Remap squad team names to Elo naming convention
    team_scores = {TEAM_NAME_MAP_SQUAD_TO_ELO.get(t, t): v for t, v in team_scores.items()}
    squad_z = z_scores(team_scores)

    # Sigma of Elo across the WC teams (the ones we have squads for)
    elo_vals = [elo_snapshot.get(t, 1500.0) for t in squad_z.keys()]
    mu = sum(elo_vals) / len(elo_vals)
    sigma = (sum((x - mu) ** 2 for x in elo_vals) / len(elo_vals)) ** 0.5

    def rating_fn(team: str) -> float:
        elo = elo_snapshot.get(team, 1500.0)
        z = squad_z.get(team)
        if z is None:
            return elo  # Fallback for a team with no squad data
        return elo + beta * z * sigma

    debug = {
        t: {
            "elo": elo_snapshot.get(t, 1500.0),
            "squad_score_m": team_scores.get(t, 0) / 1e6,
            "squad_z": squad_z.get(t, 0),
            "composite": elo_snapshot.get(t, 1500.0) + beta * squad_z.get(t, 0) * sigma,
        }
        for t in squad_z.keys()
    }
    return rating_fn, debug


def calibrate_beta(
    years: list[int] = (2018, 2022),
    gender: str = "men",
    betas=None,
    sigma: float = 0.0,
) -> dict:
    """Grid search beta minimizing mean Brier. sigma fixes the rating uncertainty."""
    if betas is None:
        betas = [round(x * 0.05, 2) for x in range(0, 11)]  # 0.00 to 0.50 by 0.05

    # Baseline pure Elo for each year (at the given sigma)
    baseline = {}
    for y in years:
        r = backtest_worldcup(y, gender=gender, sigma=sigma)
        baseline[y] = {"brier": r["mean_brier"], "log_loss": r["mean_log_loss"]}

    # Grid search
    results = []
    for b in betas:
        row = {"beta": b}
        total_brier = 0.0
        total_loss = 0.0
        total_matches = 0
        for y in years:
            fn, _ = composite_ratings_fn(y, gender=gender, beta=b)
            r = backtest_worldcup(y, ratings_fn=fn, gender=gender, sigma=sigma)
            row[f"brier_{y}"] = r["mean_brier"]
            row[f"log_loss_{y}"] = r["mean_log_loss"]
            total_brier += r["mean_brier"] * r["n_matches"]
            total_loss += r["mean_log_loss"] * r["n_matches"]
            total_matches += r["n_matches"]
        row["brier_pooled"] = total_brier / total_matches
        row["log_loss_pooled"] = total_loss / total_matches
        results.append(row)

    best = min(results, key=lambda r: r["brier_pooled"])
    return {"baseline": baseline, "grid": results, "best": best, "sigma": sigma}


def joint_calibrate(
    years: list[int] = (2018, 2022),
    gender: str = "men",
    betas: list[float] = None,
    sigmas: list[float] = None,
) -> dict:
    """Joint grid search over (beta, sigma) minimizing pooled Brier."""
    if betas is None:
        betas = [0.0, 0.05, 0.1, 0.15, 0.2, 0.3]
    if sigmas is None:
        sigmas = [0, 40, 60, 80, 100, 120, 150]

    # Baseline pure Elo
    base_total = 0.0; base_n = 0
    for y in years:
        r = backtest_worldcup(y, gender=gender, sigma=0)
        base_total += r["mean_brier"] * r["n_matches"]
        base_n += r["n_matches"]
    baseline_brier = base_total / base_n

    results = []
    for b in betas:
        for s in sigmas:
            total_brier = 0.0
            total_loss = 0.0
            total_n = 0
            for y in years:
                if b > 0:
                    fn, _ = composite_ratings_fn(y, gender=gender, beta=b)
                else:
                    meta = WC_METADATA[y]
                    ratings = snapshot_ratings(gender=gender, through_date=meta["kickoff"])
                    fn = lambda team, r=ratings: r.get(team, 1500.0)
                r = backtest_worldcup(y, ratings_fn=fn, gender=gender, sigma=s)
                total_brier += r["mean_brier"] * r["n_matches"]
                total_loss += r["mean_log_loss"] * r["n_matches"]
                total_n += r["n_matches"]
            results.append({
                "beta": b, "sigma": s,
                "brier_pooled": total_brier / total_n,
                "log_loss_pooled": total_loss / total_n,
                "brier_lift_pct": (baseline_brier - total_brier / total_n) / baseline_brier * 100,
            })
    best = min(results, key=lambda r: r["brier_pooled"])
    return {"baseline_brier": baseline_brier, "grid": results, "best": best}


def cross_validate(gender: str = "men") -> dict:
    """Fit beta on one WC, score on the other."""
    out = {}
    for train_year, test_year in [(2018, 2022), (2022, 2018)]:
        # Fit on train_year
        cal = calibrate_beta(years=[train_year], gender=gender)
        beta = cal["best"]["beta"]
        # Score on test_year
        fn, _ = composite_ratings_fn(test_year, gender=gender, beta=beta)
        r = backtest_worldcup(test_year, ratings_fn=fn, gender=gender)
        # Baseline on test_year
        base = backtest_worldcup(test_year, gender=gender)
        out[f"train_{train_year}_test_{test_year}"] = {
            "beta": beta,
            "test_brier_composite": r["mean_brier"],
            "test_brier_elo_baseline": base["mean_brier"],
            "brier_lift_pct": (base["mean_brier"] - r["mean_brier"]) / base["mean_brier"] * 100,
        }
    return out


def main() -> None:
    p = argparse.ArgumentParser(
        prog="football-elo-backtest",
        description="Backtest WC predictions on historical tournaments.",
    )
    p.add_argument("--year", type=int, choices=[2018, 2022])
    p.add_argument("--model", default="elo", choices=["elo", "composite"])
    p.add_argument("--beta", type=float, default=0.0,
                   help="Blend weight for composite model (ignored for elo)")
    p.add_argument("--gender", default="men", choices=["men", "women"])
    p.add_argument("--show-matches", type=int, default=0)
    p.add_argument("--calibrate", action="store_true",
                   help="Grid search beta across 2018+2022 and report best")
    p.add_argument("--calibrate-sigma", action="store_true",
                   help="Grid search rating-uncertainty sigma across 2018+2022")
    p.add_argument("--joint-calibrate", action="store_true",
                   help="2D grid search over (beta, sigma)")
    p.add_argument("--cross-validate", action="store_true",
                   help="Fit beta on one WC, test on the other")
    p.add_argument("--sigma", type=float, default=0.0,
                   help="Rating-uncertainty std dev (Elo points) for a single run")
    args = p.parse_args()

    if args.calibrate:
        cal = calibrate_beta(gender=args.gender)
        print(f"=== Calibration (men's WCs 2018+2022) ===")
        print(f"Baseline pure Elo per-year Brier:")
        for y, b in cal["baseline"].items():
            print(f"  {y}: brier={b['brier']:.4f}  log_loss={b['log_loss']:.4f}")
        print(f"\nGrid search over beta:")
        print(f"  {'beta':>5}  {'B_2018':>8}  {'B_2022':>8}  {'B_pool':>8}  {'LL_pool':>8}")
        for r in cal["grid"]:
            print(f"  {r['beta']:>5.2f}  {r['brier_2018']:>8.4f}  "
                  f"{r['brier_2022']:>8.4f}  {r['brier_pooled']:>8.4f}  "
                  f"{r['log_loss_pooled']:>8.4f}")
        b = cal["best"]
        print(f"\nBest: beta={b['beta']}  pooled_brier={b['brier_pooled']:.4f}  "
              f"pooled_log_loss={b['log_loss_pooled']:.4f}")
        return

    if args.calibrate_sigma:
        cal = calibrate_sigma(gender=args.gender)
        print(f"=== Sigma calibration (men's WCs 2018+2022) ===")
        print(f"  {'sigma':>6}  {'B_2018':>8}  {'B_2022':>8}  {'B_pool':>8}  {'LL_pool':>8}")
        for r in cal["grid"]:
            print(f"  {r['sigma']:>6.0f}  {r['brier_2018']:>8.4f}  "
                  f"{r['brier_2022']:>8.4f}  {r['brier_pooled']:>8.4f}  "
                  f"{r['log_loss_pooled']:>8.4f}")
        b = cal["best"]
        print(f"\nBest: sigma={b['sigma']}  pooled_brier={b['brier_pooled']:.4f}  "
              f"pooled_log_loss={b['log_loss_pooled']:.4f}")
        return

    if args.joint_calibrate:
        cal = joint_calibrate(gender=args.gender)
        print(f"=== Joint (beta, sigma) calibration — baseline Brier {cal['baseline_brier']:.4f} ===")
        # Build a matrix view: rows=beta, cols=sigma
        betas = sorted(set(r["beta"] for r in cal["grid"]))
        sigmas = sorted(set(r["sigma"] for r in cal["grid"]))
        header = "  beta\\sigma " + "".join(f"{s:>8}" for s in sigmas)
        print(header)
        for b in betas:
            line = f"  beta={b:<5.2f} "
            for s in sigmas:
                cell = next(r for r in cal["grid"] if r["beta"] == b and r["sigma"] == s)
                line += f"{cell['brier_pooled']:>8.4f}"
            print(line)
        bst = cal["best"]
        print(f"\nBest: beta={bst['beta']}  sigma={bst['sigma']}  "
              f"brier_pooled={bst['brier_pooled']:.4f}  lift={bst['brier_lift_pct']:+.2f}%")
        return

    if args.cross_validate:
        cv = cross_validate(gender=args.gender)
        print(f"=== Cross-validation ===")
        for k, v in cv.items():
            print(f"\n{k}:")
            print(f"  best beta        = {v['beta']}")
            print(f"  test Brier (elo) = {v['test_brier_elo_baseline']:.4f}")
            print(f"  test Brier (cmp) = {v['test_brier_composite']:.4f}")
            print(f"  lift             = {v['brier_lift_pct']:+.2f}%")
        return

    if not args.year:
        raise SystemExit("Need --year, or use --calibrate / --cross-validate")

    if args.model == "elo":
        result = backtest_worldcup(args.year, gender=args.gender, sigma=args.sigma)
    else:
        fn, _ = composite_ratings_fn(args.year, gender=args.gender, beta=args.beta)
        result = backtest_worldcup(args.year, ratings_fn=fn, gender=args.gender, sigma=args.sigma)

    header = f"=== {args.year} {args.gender}'s WC — {args.model} model"
    if args.model == "composite":
        header += f" (beta={args.beta})"
    header += " ==="
    print(header)
    print(f"Matches        : {result['n_matches']}")
    print(f"Mean Brier     : {result['mean_brier']:.4f}")
    print(f"Mean log-loss  : {result['mean_log_loss']:.4f}")

    if args.show_matches > 0:
        print(f"\nFirst {args.show_matches} matches:")
        for m in result["per_match"][: args.show_matches]:
            print(
                f"  {m['date']} {m['home']:24s} {m['score']:>5} {m['away']:<24s} "
                f"| {int(m['p_home']*100):>2d}/{int(m['p_draw']*100):>2d}/{int(m['p_away']*100):>2d}"
                f" Brier {m['brier']:.3f}"
            )


if __name__ == "__main__":
    main()
