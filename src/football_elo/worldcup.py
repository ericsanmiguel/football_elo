"""2026 World Cup full tournament predictions using Elo ratings."""

import json
import math
import random
import re
import unicodedata
from itertools import combinations
from pathlib import Path

from .elo import expected_result
from .config import HOME_ADVANTAGE
from .pipeline import EloSystem


def slugify(name: str) -> str:
    s = unicodedata.normalize("NFKD", name)
    s = s.encode("ascii", "ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    s = re.sub(r"-+", "-", s)
    return s


# 2026 FIFA World Cup groups
GROUPS_2026 = {
    "A": ["Mexico", "South Africa", "South Korea", "Czech Republic"],
    "B": ["Canada", "Bosnia and Herzegovina", "Qatar", "Switzerland"],
    "C": ["Brazil", "Morocco", "Haiti", "Scotland"],
    "D": ["United States", "Paraguay", "Australia", "Turkey"],
    "E": ["Germany", "Curacao", "Ivory Coast", "Ecuador"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Egypt", "Iran", "New Zealand"],
    "H": ["Spain", "Cape Verde", "Saudi Arabia", "Uruguay"],
    "I": ["France", "Senegal", "Iraq", "Norway"],
    "J": ["Argentina", "Algeria", "Austria", "Jordan"],
    "K": ["Portugal", "DR Congo", "Uzbekistan", "Colombia"],
    "L": ["England", "Croatia", "Ghana", "Panama"],
}

HOST_NATIONS = {"United States", "Mexico", "Canada"}

# Match schedule: group -> [(team_a, team_b, date, venue), ...]
MATCH_SCHEDULE = {
    "A": [
        (0, 1, "Jun 11", "Mexico City"),
        (2, 3, "Jun 11", "Guadalajara"),
        (3, 1, "Jun 18", "Atlanta"),
        (0, 2, "Jun 18", "Guadalajara"),
        (3, 0, "Jun 24", "Mexico City"),
        (1, 2, "Jun 24", "Guadalajara"),
    ],
    "B": [
        (0, 1, "Jun 12", "Toronto"),
        (2, 3, "Jun 13", "Santa Clara"),
        (3, 1, "Jun 18", "Inglewood"),
        (0, 2, "Jun 18", "Vancouver"),
        (3, 0, "Jun 24", "Vancouver"),
        (1, 2, "Jun 24", "Seattle"),
    ],
    "C": [
        (0, 1, "Jun 13", "East Rutherford"),
        (2, 3, "Jun 13", "Foxborough"),
        (3, 1, "Jun 19", "Foxborough"),
        (0, 2, "Jun 19", "Philadelphia"),
        (3, 0, "Jun 24", "Miami"),
        (1, 2, "Jun 24", "Atlanta"),
    ],
    "D": [
        (0, 1, "Jun 12", "Inglewood"),
        (2, 3, "Jun 13", "Vancouver"),
        (0, 2, "Jun 19", "Seattle"),
        (3, 1, "Jun 19", "Santa Clara"),
        (3, 0, "Jun 25", "Inglewood"),
        (1, 2, "Jun 25", "Santa Clara"),
    ],
    "E": [
        (0, 1, "Jun 14", "Houston"),
        (2, 3, "Jun 14", "Philadelphia"),
        (0, 2, "Jun 20", "Toronto"),
        (3, 1, "Jun 20", "Kansas City"),
        (3, 0, "Jun 25", "East Rutherford"),
        (1, 2, "Jun 25", "Philadelphia"),
    ],
    "F": [
        (0, 1, "Jun 14", "Arlington"),
        (2, 3, "Jun 14", "Guadalajara"),
        (0, 2, "Jun 20", "Houston"),
        (3, 1, "Jun 20", "Guadalajara"),
        (1, 2, "Jun 25", "Arlington"),
        (3, 0, "Jun 25", "Kansas City"),
    ],
    "G": [
        (0, 1, "Jun 15", "Seattle"),
        (2, 3, "Jun 15", "Inglewood"),
        (0, 2, "Jun 21", "Inglewood"),
        (3, 1, "Jun 21", "Vancouver"),
        (1, 2, "Jun 26", "Seattle"),
        (3, 0, "Jun 26", "Vancouver"),
    ],
    "H": [
        (0, 1, "Jun 15", "Atlanta"),
        (2, 3, "Jun 15", "Miami"),
        (0, 2, "Jun 21", "Atlanta"),
        (3, 1, "Jun 21", "Miami"),
        (1, 2, "Jun 26", "Houston"),
        (3, 0, "Jun 26", "Guadalajara"),
    ],
    "I": [
        (0, 1, "Jun 16", "East Rutherford"),
        (2, 3, "Jun 16", "Foxborough"),
        (0, 2, "Jun 22", "Philadelphia"),
        (3, 1, "Jun 22", "East Rutherford"),
        (3, 0, "Jun 26", "Foxborough"),
        (1, 2, "Jun 26", "Toronto"),
    ],
    "J": [
        (0, 1, "Jun 16", "Kansas City"),
        (2, 3, "Jun 16", "Santa Clara"),
        (0, 2, "Jun 22", "Arlington"),
        (3, 1, "Jun 22", "Santa Clara"),
        (1, 2, "Jun 27", "Kansas City"),
        (3, 0, "Jun 27", "Arlington"),
    ],
    "K": [
        (0, 1, "Jun 17", "Houston"),
        (2, 3, "Jun 17", "Mexico City"),
        (0, 2, "Jun 23", "Houston"),
        (3, 1, "Jun 23", "Guadalajara"),
        (3, 0, "Jun 27", "Miami"),
        (1, 2, "Jun 27", "Atlanta"),
    ],
    "L": [
        (0, 1, "Jun 17", "Arlington"),
        (2, 3, "Jun 17", "Toronto"),
        (0, 2, "Jun 23", "Foxborough"),
        (3, 1, "Jun 23", "Toronto"),
        (3, 0, "Jun 27", "East Rutherford"),
        (1, 2, "Jun 27", "Philadelphia"),
    ],
}

# R32 bracket: each entry is (team_a_source, team_b_source)
# Sources: "1X" = winner of group X, "2X" = runner-up of group X, "3" = 3rd place slot
# R32 matches pair into R16 matches (consecutive pairs)
R32_BRACKET = [
    ("2A", "2B"),    # M73 → R16 top half
    ("1E", "3"),     # M74 (3rd place slot 0)
    ("1F", "2C"),    # M75
    ("1C", "2F"),    # M76
    ("1I", "3"),     # M77 (3rd place slot 1)
    ("2E", "2I"),    # M78
    ("1A", "3"),     # M79 (3rd place slot 2)
    ("1L", "3"),     # M80 (3rd place slot 3)
    ("1D", "3"),     # M81 (3rd place slot 4)
    ("1G", "3"),     # M82 (3rd place slot 5)
    ("2K", "2L"),    # M83
    ("1H", "2J"),    # M84
    ("1B", "3"),     # M85 (3rd place slot 6)
    ("1J", "2H"),    # M86
    ("1K", "3"),     # M87 (3rd place slot 7)
    ("2D", "2G"),    # M88
]

# Which group winners face 3rd-place teams (indices into R32_BRACKET)
THIRD_PLACE_SLOTS = [1, 4, 6, 7, 8, 9, 12, 14]
# The group winners at those slots
THIRD_PLACE_OPPONENTS = ["E", "I", "A", "L", "D", "G", "B", "K"]

# Tournament calendar boundaries used to classify played results.
# Group stage runs Jun 11-27; the Round of 32 starts Jun 28.
GROUP_STAGE_START = "2026-06-09"
KNOCKOUT_START = "2026-06-28"


def collect_results(elo: EloSystem):
    """Extract played 2026 World Cup results from the Elo match history.

    Returns (group_results, knockout_results, results_through):
      group_results: {group: {(i, j): (goals_i, goals_j)}} with i < j
        indexing into GROUPS_2026[group].
      knockout_results: [{"team_a", "team_b", "score": [a, b], "winner",
        "pens": bool, "date"}, ...] in chronological order.
      results_through: ISO date of the latest played match, or None.
    """
    team_to_group = {t: g for g, teams in GROUPS_2026.items() for t in teams}
    group_results: dict[str, dict] = {}
    knockout_results: list[dict] = []
    results_through = None

    for rec in elo.history:
        if not rec.get("is_home") or rec["tournament"] != "FIFA World Cup":
            continue
        date = str(rec["date"])[:10]
        if date < GROUP_STAGE_START:
            continue
        home, away = rec["team"], rec["opponent"]
        if team_to_group.get(home) is None or team_to_group.get(away) is None:
            continue
        hs, as_ = int(rec["team_score"]), int(rec["opponent_score"])

        if date < KNOCKOUT_START:
            g = team_to_group[home]
            if team_to_group[away] != g:
                continue
            teams = GROUPS_2026[g]
            hi, ai = teams.index(home), teams.index(away)
            key = (min(hi, ai), max(hi, ai))
            goals = (hs, as_) if hi < ai else (as_, hs)
            group_results.setdefault(g, {})[key] = goals
        else:
            shootout = rec.get("shootout_winner")
            if hs > as_:
                winner = home
            elif as_ > hs:
                winner = away
            else:
                # Level after extra time — decided on penalties
                winner = shootout if shootout in (home, away) else home
            knockout_results.append({
                "team_a": home, "team_b": away,
                "score": [hs, as_],
                "winner": winner,
                "pens": hs == as_,
                "date": date,
            })

        if results_through is None or date > results_through:
            results_through = date

    return group_results, knockout_results, results_through


# Poisson score model parameters. Calibrated by
# src/football_elo/calibrate_poisson.py against 64,202 team-match rows
# from men's international results since 1990. The dr^2 term is
# negative, encoding sublinearity in the rating gap — without it the
# linear model extrapolates badly into the high-|dr| regime that the
# WC2026 simulator's rating-noise generator can produce.
GOAL_BASELINE = 1.2414
GOAL_ELO_SCALING = 0.002174
GOAL_ELO_SCALING_SQ = -5.246e-7


def _expected_goals(rating_a: float, rating_b: float, ha: float = 0.0):
    """Compute expected goals for each team using the Poisson model.

    dr = (rating_a + ha) - rating_b, using the same +50 home rule as Elo.
    Returns (lambda_a, lambda_b).
    """
    dr = (rating_a + ha) - rating_b
    quad = GOAL_ELO_SCALING_SQ * dr * dr
    lam_a = GOAL_BASELINE * math.exp(GOAL_ELO_SCALING * dr + quad)
    lam_b = GOAL_BASELINE * math.exp(-GOAL_ELO_SCALING * dr + quad)
    return lam_a, lam_b


def _poisson_pmf(k: int, lam: float) -> float:
    """Poisson probability mass function."""
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def match_probabilities(
    rating_a: float, rating_b: float, home_team: str = "", neutral: bool = True
) -> tuple[float, float, float]:
    """Compute P(win_a), P(draw), P(win_b) from Elo ratings using Poisson model."""
    ha = 0.0
    if not neutral and home_team:
        ha = HOME_ADVANTAGE
    lam_a, lam_b = _expected_goals(rating_a, rating_b, ha)

    p_win = 0.0
    p_draw = 0.0
    p_loss = 0.0
    max_goals = 10

    for i in range(max_goals + 1):
        pi = _poisson_pmf(i, lam_a)
        for j in range(max_goals + 1):
            pj = _poisson_pmf(j, lam_b)
            p = pi * pj
            if i > j:
                p_win += p
            elif i == j:
                p_draw += p
            else:
                p_loss += p

    total = p_win + p_draw + p_loss
    return p_win / total, p_draw / total, p_loss / total


def simulate_group_match(
    rating_a: float, rating_b: float, ha: float = 0.0
) -> tuple[int, int]:
    """Simulate a group stage match using Poisson model. Returns (goals_a, goals_b)."""
    lam_a, lam_b = _expected_goals(rating_a, rating_b, ha)
    goals_a = _poisson_sample(lam_a)
    goals_b = _poisson_sample(lam_b)
    return goals_a, goals_b


def simulate_knockout_match(
    rating_a: float, rating_b: float, team_a: str, team_b: str
) -> str:
    """Simulate a knockout match using Poisson. If draw, penalty shootout."""
    is_neutral = team_a not in HOST_NATIONS and team_b not in HOST_NATIONS
    ha = 0.0
    if not is_neutral:
        if team_a in HOST_NATIONS:
            ha = HOME_ADVANTAGE
        elif team_b in HOST_NATIONS:
            ha = -HOME_ADVANTAGE

    goals_a, goals_b = simulate_group_match(rating_a, rating_b, ha)
    if goals_a > goals_b:
        return team_a
    if goals_b > goals_a:
        return team_b
    # Draw — penalty shootout decided by Elo expected result
    we_a = expected_result(rating_a + ha, rating_b)
    return team_a if random.random() < we_a else team_b


def _poisson_sample(lam: float) -> int:
    """Sample from Poisson distribution using inverse transform."""
    L = math.exp(-lam)
    k = 0
    p = 1.0
    while True:
        k += 1
        p *= random.random()
        if p < L:
            return k - 1


def _rank_tied_block(block, played, gd, gf, rand_keys):
    """Order a set of teams level on points by the 2026 head-to-head rules.

    ``block`` is a list of team indices known to be level on competition
    points (or, in a recursive call, on a higher head-to-head criterion).
    ``played`` maps (i, j) with i < j to (goals_i, goals_j) for every group
    match. ``gd``/``gf`` are overall (all-matches) totals and ``rand_keys``
    gives a stable per-team value for the final, unmodelled break.

    Criteria, in FIFA 2026 order: head-to-head points, head-to-head goal
    difference, head-to-head goals scored — re-applied to any still-level
    subset — then overall goal difference, overall goals scored, and a
    random draw standing in for fair-play points / the FIFA World Ranking.
    """
    if len(block) == 1:
        return list(block)

    bset = set(block)
    h2h_pts = {x: 0 for x in block}
    h2h_gd = {x: 0 for x in block}
    h2h_gf = {x: 0 for x in block}
    for (i, j), (gi, gj) in played.items():
        if i in bset and j in bset:
            h2h_gf[i] += gi
            h2h_gf[j] += gj
            h2h_gd[i] += gi - gj
            h2h_gd[j] += gj - gi
            if gi > gj:
                h2h_pts[i] += 3
            elif gj > gi:
                h2h_pts[j] += 3
            else:
                h2h_pts[i] += 1
                h2h_pts[j] += 1

    ordered = sorted(
        block, key=lambda x: (h2h_pts[x], h2h_gd[x], h2h_gf[x]), reverse=True
    )

    # Partition the head-to-head ordering into runs still level on all three
    # head-to-head criteria.
    runs = []
    k = 0
    while k < len(ordered):
        m = k + 1
        while m < len(ordered) and (
            h2h_pts[ordered[m]] == h2h_pts[ordered[k]]
            and h2h_gd[ordered[m]] == h2h_gd[ordered[k]]
            and h2h_gf[ordered[m]] == h2h_gf[ordered[k]]
        ):
            m += 1
        runs.append(ordered[k:m])
        k = m

    if len(runs) == 1:
        # Head-to-head separated no one: fall through to overall criteria.
        return sorted(
            block, key=lambda x: (gd[x], gf[x], rand_keys[x]), reverse=True
        )

    # Head-to-head split the block; re-apply it within each still-level run.
    result = []
    for run in runs:
        result.extend(_rank_tied_block(run, played, gd, gf, rand_keys))
    return result


def _rank_group(n, points, gd, gf, played, rand_keys):
    """Order teams 0..n-1 under the 2026 World Cup group tie-breaking rules.

    Teams are first split by competition points; each block level on points
    is then resolved by _rank_tied_block. Returns team indices, best first.
    """
    by_points = sorted(range(n), key=lambda x: points[x], reverse=True)
    order = []
    k = 0
    while k < len(by_points):
        m = k + 1
        while m < len(by_points) and points[by_points[m]] == points[by_points[k]]:
            m += 1
        order.extend(_rank_tied_block(by_points[k:m], played, gd, gf, rand_keys))
        k = m
    return order


def simulate_group_once(
    teams: list[str], match_params: dict,
    fixed_results: dict | None = None,
) -> list[tuple[str, int, int, int]]:
    """Simulate one group once using Poisson scores.

    fixed_results maps (i, j) with i < j to actual (goals_i, goals_j) for
    matches already played — those are taken as given instead of simulated.

    Teams are ranked by the 2026 World Cup tie-breaking rules: points, then
    head-to-head record among level teams (points, goal difference, goals
    scored), then overall goal difference and goals scored (see _rank_group).

    Returns [(team, points, gd, gf), ...] sorted by standing.
    """
    n = len(teams)
    points = [0] * n
    gd = [0] * n
    gf = [0] * n
    played: dict[tuple[int, int], tuple[int, int]] = {}

    for i, j in combinations(range(n), 2):
        if fixed_results and (i, j) in fixed_results:
            goals_a, goals_b = fixed_results[(i, j)]
        else:
            ra, rb, ha = match_params[(i, j)]
            goals_a, goals_b = simulate_group_match(ra, rb, ha)

        played[(i, j)] = (goals_a, goals_b)
        gf[i] += goals_a
        gf[j] += goals_b
        gd[i] += goals_a - goals_b
        gd[j] += goals_b - goals_a

        if goals_a > goals_b:
            points[i] += 3
        elif goals_b > goals_a:
            points[j] += 3
        else:
            points[i] += 1
            points[j] += 1

    rand_keys = [random.random() for _ in range(n)]
    order = _rank_group(n, points, gd, gf, played, rand_keys)
    return [(teams[idx], points[idx], gd[idx], gf[idx]) for idx in order]


def _precompute_group_params(
    teams: list[str], ratings: dict[str, float]
) -> dict:
    """Pre-compute match parameters (ratings + home advantage) for a group."""
    matchups = list(combinations(range(4), 2))
    match_params = {}
    for i, j in matchups:
        team_a, team_b = teams[i], teams[j]
        is_neutral = team_a not in HOST_NATIONS and team_b not in HOST_NATIONS
        home = team_a if team_a in HOST_NATIONS else (
            team_b if team_b in HOST_NATIONS else ""
        )

        ra = ratings.get(team_a, 1500)
        rb = ratings.get(team_b, 1500)
        ha = 0.0
        if not is_neutral:
            if home == team_a:
                ha = HOME_ADVANTAGE
            elif home == team_b:
                ha = -HOME_ADVANTAGE

        match_params[(i, j)] = (ra, rb, ha)
    return match_params


def allocate_third_place(
    qualifying_thirds: list[tuple[str, str, int, int, int]],
) -> dict[int, str]:
    """Assign 8 qualifying 3rd-place teams to bracket slots.

    qualifying_thirds: [(team_name, group_letter, points, gd, gf), ...]
    Returns: {slot_index: team_name} for the 8 THIRD_PLACE_SLOTS.
    """
    # Sort by group letter for consistent allocation
    by_group = {g: team for team, g, *_ in qualifying_thirds}
    available_groups = sorted(by_group.keys())

    assignment = {}
    used_groups = set()

    for slot_idx, opponent_group in zip(THIRD_PLACE_SLOTS, THIRD_PLACE_OPPONENTS):
        # Find a 3rd-place team that isn't from the opponent's group
        for g in available_groups:
            if g not in used_groups and g != opponent_group:
                assignment[slot_idx] = by_group[g]
                used_groups.add(g)
                break
        else:
            # Fallback: assign any remaining
            for g in available_groups:
                if g not in used_groups:
                    assignment[slot_idx] = by_group[g]
                    used_groups.add(g)
                    break

    return assignment


def simulate_tournament(
    ratings: dict[str, float], n_sims: int = 50000,
    rating_sigma: float = 0.0,
    group_results: dict | None = None,
    knockout_winners: dict | None = None,
) -> dict[str, dict]:
    """Run full tournament Monte Carlo simulation.

    rating_sigma > 0 samples each team's rating from N(mu, sigma) once per
    simulation — captures uncertainty in the point-estimate Elo. Default 0
    preserves the pre-existing deterministic behavior.

    group_results ({group: {(i, j): (goals_i, goals_j)}}) and
    knockout_winners ({frozenset({team_a, team_b}): winner}) hold matches
    already played; the simulation conditions on them instead of sampling.

    Returns per-team dict with counts for each round reached.
    """
    # Initialize counters
    all_teams = []
    for teams in GROUPS_2026.values():
        all_teams.extend(teams)

    # Pre-compute group params only when ratings are deterministic (sigma=0).
    # With sigma>0 we re-compute per simulation since ratings change.
    group_params = None
    if rating_sigma <= 0:
        group_params = {}
        for g, teams in GROUPS_2026.items():
            group_params[g] = _precompute_group_params(teams, ratings)

    counts = {
        team: {"gs": 0, "r32": 0, "r16": 0, "qf": 0, "sf": 0, "final": 0, "winner": 0}
        for team in all_teams
    }
    # Also track group finishing position
    pos_counts = {team: [0, 0, 0, 0] for team in all_teams}

    for _ in range(n_sims):
        # Sample per-sim ratings if uncertainty is enabled
        if rating_sigma > 0:
            sim_ratings = {
                t: ratings.get(t, 1500.0) + random.gauss(0, rating_sigma)
                for t in all_teams
            }
            sim_group_params = {
                g: _precompute_group_params(teams, sim_ratings)
                for g, teams in GROUPS_2026.items()
            }
        else:
            sim_ratings = ratings
            sim_group_params = group_params

        # 1. Simulate all groups (conditioning on played results)
        standings = {}  # group -> [(team, pts, gd), ...]
        for g, teams in GROUPS_2026.items():
            fixed = group_results.get(g) if group_results else None
            standings[g] = simulate_group_once(teams, sim_group_params[g], fixed)

        # Record group positions
        for g, standing in standings.items():
            for pos, (team, _pts, _gd, _gf) in enumerate(standing):
                pos_counts[team][pos] += 1

        # 2. Determine R32 qualifiers
        # 1st and 2nd from each group
        group_1st = {g: s[0][0] for g, s in standings.items()}
        group_2nd = {g: s[1][0] for g, s in standings.items()}

        # 3rd place: rank all 12, take best 8
        thirds = []
        for g, s in standings.items():
            team, pts, gd, gf = s[2]
            thirds.append((team, g, pts, gd, gf))
        # Third-placed teams come from different groups and never meet, so
        # head-to-head cannot apply: rank by points, goal difference, goals
        # scored (then fair play / FIFA ranking, here a random draw).
        thirds.sort(key=lambda x: (x[2], x[3], x[4], random.random()), reverse=True)
        qualifying_thirds = thirds[:8]

        # All R32 qualifiers advance
        r32_teams = set()
        for t in group_1st.values():
            r32_teams.add(t)
        for t in group_2nd.values():
            r32_teams.add(t)
        for t, *_ in qualifying_thirds:
            r32_teams.add(t)

        for t in r32_teams:
            counts[t]["r32"] += 1

        # 3. Assign 3rd-place teams to bracket
        third_assignment = allocate_third_place(qualifying_thirds)

        # 4. Build R32 matchups
        r32_matchups = []
        for idx, (src_a, src_b) in enumerate(R32_BRACKET):
            # Resolve team A
            if src_a.startswith("1"):
                team_a = group_1st[src_a[1]]
            elif src_a.startswith("2"):
                team_a = group_2nd[src_a[1]]
            else:
                team_a = third_assignment[idx]

            # Resolve team B
            if src_b.startswith("1"):
                team_b = group_1st[src_b[1]]
            elif src_b.startswith("2"):
                team_b = group_2nd[src_b[1]]
            else:
                team_b = third_assignment[idx]

            r32_matchups.append((team_a, team_b))

        # 5. Simulate knockout rounds
        # R32 (16 matches) → R16 (8) → QF (4) → SF (2) → Final (1) → Winner
        current_round = r32_matchups  # 16 matches
        round_names = ["r16", "qf", "sf", "final", "winner"]

        for round_name in round_names:
            winners = []
            for team_a, team_b in current_round:
                w = None
                if knockout_winners:
                    w = knockout_winners.get(frozenset((team_a, team_b)))
                if w is None:
                    w = simulate_knockout_match(
                        sim_ratings.get(team_a, 1500), sim_ratings.get(team_b, 1500),
                        team_a, team_b,
                    )
                winners.append(w)
                counts[w][round_name] += 1

            # Pair winners for next round
            if len(winners) >= 2:
                current_round = [
                    (winners[i], winners[i + 1])
                    for i in range(0, len(winners), 2)
                ]
            else:
                break  # Tournament complete

    # Convert to probabilities
    results = {}
    for team in all_teams:
        c = counts[team]
        pc = pos_counts[team]
        results[team] = {
            "p_1st": round(pc[0] / n_sims * 100, 1),
            "p_2nd": round(pc[1] / n_sims * 100, 1),
            "p_3rd": round(pc[2] / n_sims * 100, 1),
            "p_4th": round(pc[3] / n_sims * 100, 1),
            "p_r32": round(c["r32"] / n_sims * 100, 1),
            "p_r16": round(c["r16"] / n_sims * 100, 1),
            "p_qf": round(c["qf"] / n_sims * 100, 1),
            "p_sf": round(c["sf"] / n_sims * 100, 1),
            "p_final": round(c["final"] / n_sims * 100, 1),
            "p_winner": round(c["winner"] / n_sims * 100, 1),
        }

    return results


# Composite-rating parameters calibrated on 2018+2022 men's WCs
# (see docs/methodology_appendix.tex and src/football_elo/backtest.py).
SQUAD_BETA = 0.25
RATING_SIGMA = 120.0


def _compose_ratings(
    base_ratings: dict[str, float], beta: float,
) -> tuple[dict[str, float], dict[str, float]]:
    """Blend base Elo with log-transformed age-adjusted squad z-score.

    Returns (composite_ratings, squad_z_scores). squad_z is empty dict if
    squad data is unavailable.
    """
    if beta <= 0:
        return dict(base_ratings), {}
    try:
        from .squad_strength import load_tournament_squads, squad_scores, z_scores
        squads = load_tournament_squads(2026)
    except FileNotFoundError:
        return dict(base_ratings), {}
    scores = squad_scores(squads, use_log=True)
    z = z_scores(scores)
    vals = list(base_ratings.values())
    mu = sum(vals) / len(vals)
    sigma_elo = (sum((v - mu) ** 2 for v in vals) / len(vals)) ** 0.5
    composite = {t: base_ratings[t] + beta * z.get(t, 0.0) * sigma_elo for t in base_ratings}
    return composite, z


def _to_index(values_by_team: dict[str, float]) -> dict[str, float]:
    """Linearly rescale a dict of floats to the 50–100 range.

    Min value maps to 50, max to 100. Purely a display transform; the
    underlying math (composite rating, squad z) is unchanged.
    """
    if not values_by_team:
        return {}
    vs = list(values_by_team.values())
    lo, hi = min(vs), max(vs)
    if hi - lo < 1e-9:
        return {t: 75.0 for t in values_by_team}
    return {t: 50.0 + 50.0 * (v - lo) / (hi - lo) for t, v in values_by_team.items()}


def _marginal_match_probs(
    rating_a: float, rating_b: float, home: str, neutral: bool,
    sigma: float, n_samples: int, rng: random.Random,
) -> tuple[float, float, float]:
    """match_probabilities marginalized over independent rating noise ~N(0, sigma)."""
    if sigma <= 0:
        return match_probabilities(rating_a, rating_b, home_team=home, neutral=neutral)
    pw = pd_ = pl = 0.0
    for _ in range(n_samples):
        ra = rating_a + rng.gauss(0, sigma)
        rb = rating_b + rng.gauss(0, sigma)
        h, d, a = match_probabilities(ra, rb, home_team=home, neutral=neutral)
        pw += h; pd_ += d; pl += a
    return pw / n_samples, pd_ / n_samples, pl / n_samples


def _stage_label(group_results: dict, knockout_results: list) -> str:
    """Human-readable tournament stage implied by the played results."""
    n_group = sum(len(v) for v in group_results.values())
    n_ko = len(knockout_results)
    if n_group == 0 and n_ko == 0:
        return "Pre-tournament"
    if n_group < 72:
        md_played = [0, 0, 0]
        for g, schedule in MATCH_SCHEDULE.items():
            fixed = group_results.get(g, {})
            for k, (i, j, _date, _venue) in enumerate(schedule):
                if (min(i, j), max(i, j)) in fixed:
                    md_played[k // 2] += 1
        for md in range(3):
            if md_played[md] < 24:
                return f"Matchday {md + 1} ({md_played[md]}/24 played)"
        return "Group stage"
    if n_ko == 0:
        return "Group stage complete"
    done = 0
    for name, size in [("Round of 32", 16), ("Round of 16", 8),
                       ("Quarterfinals", 4), ("Semifinals", 2)]:
        if n_ko < done + size:
            return f"{name} ({n_ko - done}/{size} played)"
        done += size
    # 30 = semis done; 31 adds the third-place match; 32 adds the final
    if n_ko <= 31:
        return "Semifinals complete"
    return "Tournament complete"


def _write_archive(data: dict, output_dir: Path) -> None:
    """Snapshot the predictions JSON as the tournament progresses.

    While no 2026 matches have been played, maintains pre-tournament.json
    (overwritten each run so it reflects the final pre-kickoff state). Once
    results are in, writes one snapshot per results-date; runs that produce
    identical content to the latest snapshot are skipped. An index.json
    lists all snapshots for the frontend's archive selector.
    """
    archive_dir = output_dir / "worldcup_archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    index_path = archive_dir / "index.json"
    index = []
    if index_path.exists():
        index = json.loads(index_path.read_text(encoding="utf-8"))

    payload = json.dumps(data, separators=(",", ":"))
    completed = data.get("completed", 0)
    if completed == 0:
        fname = "pre-tournament.json"
        label = "Pre-tournament"
    else:
        through = data.get("results_through")
        if not through:
            return
        fname = f"{through}.json"
        label = data.get("stage", through)
        dated = [e for e in index if e["file"] != "pre-tournament.json"]
        if dated:
            latest = archive_dir / dated[-1]["file"]
            if latest.exists() and latest.read_text(encoding="utf-8") == payload:
                return

    (archive_dir / fname).write_text(payload, encoding="utf-8")
    entry = {
        "file": fname, "label": label, "completed": completed,
        "through": data.get("results_through"),
    }
    index = [e for e in index if e["file"] != fname] + [entry]
    index.sort(key=lambda e: (e["file"] != "pre-tournament.json", e["file"]))
    index_path.write_text(json.dumps(index, separators=(",", ":")), encoding="utf-8")


def export_worldcup_json(elo: EloSystem, output_dir: Path) -> None:
    """Export World Cup 2026 predictions as JSON.

    Uses composite ratings (Elo + beta * squad_z * sigma_Elo) and rating
    uncertainty in the Monte Carlo, with parameters calibrated on 2018+2022.
    If squad data is unavailable, falls back to pure Elo. Once the
    tournament is underway, played matches are taken as given: actual
    scores are exported alongside the fixtures and the Monte Carlo
    conditions on them.
    """
    random.seed(2026)

    # Played results so far (empty before kickoff)
    group_results, knockout_results, results_through = collect_results(elo)
    knockout_winners = {
        frozenset((r["team_a"], r["team_b"])): r["winner"]
        for r in knockout_results
    }

    # Base Elo per team
    base_ratings: dict[str, float] = {}
    for teams in GROUPS_2026.values():
        for t in teams:
            base_ratings[t] = elo.get_rating(t)

    # Composite ratings: base Elo + squad tilt
    all_ratings, squad_z = _compose_ratings(base_ratings, SQUAD_BETA)

    # Display-only indices rescaled to 50–100 across the 48 tournament teams
    squad_index = _to_index(squad_z) if squad_z else {}
    combined_index = _to_index(all_ratings)

    # Tournament simulation with rating uncertainty, conditioned on results
    sim_results = simulate_tournament(
        all_ratings, n_sims=10000, rating_sigma=RATING_SIGMA,
        group_results=group_results, knockout_winners=knockout_winners,
    )

    # Match-level probabilities shown on the Groups tab also marginalize over sigma
    rng = random.Random(20260611)

    groups = {}
    for group_name, teams in GROUPS_2026.items():
        team_ratings = {t: all_ratings[t] for t in teams}
        fixed = group_results.get(group_name, {})

        # Actual standings from played matches
        table = {t: {"mp": 0, "pts": 0, "gd": 0, "gf": 0} for t in teams}
        for (i, j), (gi, gj) in fixed.items():
            for idx, gf_, ga_ in ((i, gi, gj), (j, gj, gi)):
                row = table[teams[idx]]
                row["mp"] += 1
                row["gf"] += gf_
                row["gd"] += gf_ - ga_
                row["pts"] += 3 if gf_ > ga_ else (1 if gf_ == ga_ else 0)

        matches = []
        schedule = MATCH_SCHEDULE.get(group_name, [])
        for i, j, date, venue in schedule:
            team_a, team_b = teams[i], teams[j]
            is_neutral = team_a not in HOST_NATIONS and team_b not in HOST_NATIONS
            home = team_a if team_a in HOST_NATIONS else (
                team_b if team_b in HOST_NATIONS else ""
            )
            # Listed order follows the schedule, except a host plays "home"
            swap = home == team_b
            m_home, m_away = (team_b, team_a) if swap else (team_a, team_b)

            key = (min(i, j), max(i, j))
            if key in fixed:
                gi, gj = fixed[key]
                goals_a, goals_b = (gi, gj) if i < j else (gj, gi)
                score = [goals_b, goals_a] if swap else [goals_a, goals_b]
                matches.append({
                    "home": m_home, "away": m_away,
                    "score": score, "played": True,
                    "is_neutral": is_neutral if not swap else False,
                    "date": date, "venue": venue,
                })
            else:
                pa, pd, pb = _marginal_match_probs(
                    team_ratings[m_home], team_ratings[m_away],
                    home=home, neutral=is_neutral and not swap,
                    sigma=RATING_SIGMA, n_samples=400, rng=rng,
                )
                matches.append({
                    "home": m_home, "away": m_away,
                    "p_home": round(pa * 100, 1),
                    "p_draw": round(pd * 100, 1),
                    "p_away": round(pb * 100, 1),
                    "is_neutral": is_neutral if not swap else False,
                    "date": date, "venue": venue,
                })

        team_list = []
        for t in teams:
            team_list.append({
                "team": t,
                "slug": slugify(t),
                "rating": round(all_ratings[t], 0),
                "elo_base": round(base_ratings[t], 0),
                "squad_index": round(squad_index.get(t, 75.0), 1) if squad_index else None,
                "combined_index": round(combined_index.get(t, 75.0), 1),
                **table[t],
                **sim_results[t],
            })
        # Order the displayed table by the 2026 tie-breaking rules. Played
        # results (fixed) drive head-to-head; p_1st — itself head-to-head-aware
        # via the simulation — is the deterministic final break in place of a
        # random draw, so the table never contradicts the qualification odds.
        pts_arr = [table[t]["pts"] for t in teams]
        gd_arr = [table[t]["gd"] for t in teams]
        gf_arr = [table[t]["gf"] for t in teams]
        p1st_arr = [sim_results[t]["p_1st"] for t in teams]
        order = _rank_group(len(teams), pts_arr, gd_arr, gf_arr, fixed, p1st_arr)
        rank_of = {teams[idx]: pos for pos, idx in enumerate(order)}
        team_list.sort(key=lambda x: rank_of[x["team"]])

        groups[group_name] = {"teams": team_list, "matches": matches}

    n_completed = sum(len(v) for v in group_results.values()) + len(knockout_results)
    data = {
        "tournament": "2026 FIFA World Cup",
        "stage": _stage_label(group_results, knockout_results),
        "completed": n_completed,
        "results_through": results_through,
        "knockout_results": knockout_results,
        "groups": groups,
    }
    (output_dir / "worldcup2026.json").write_text(
        json.dumps(data, separators=(",", ":")), encoding="utf-8"
    )
    _write_archive(data, output_dir)
