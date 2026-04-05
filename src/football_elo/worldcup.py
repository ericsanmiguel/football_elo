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


# Poisson score model parameters (calibrated from 98K match records)
GOAL_BASELINE = 1.28      # baseline expected goals per team
GOAL_ELO_SCALING = 0.00215  # Elo scaling factor


def _expected_goals(rating_a: float, rating_b: float, ha: float = 0.0):
    """Compute expected goals for each team using the Poisson model.

    dr = (rating_a + ha) - rating_b, using the same +50 home rule as Elo.
    Returns (lambda_a, lambda_b).
    """
    dr = (rating_a + ha) - rating_b
    lam_a = GOAL_BASELINE * math.exp(GOAL_ELO_SCALING * dr)
    lam_b = GOAL_BASELINE * math.exp(-GOAL_ELO_SCALING * dr)
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


def simulate_group_once(
    teams: list[str], match_params: dict
) -> list[tuple[str, int, float]]:
    """Simulate one group once using Poisson scores.

    Returns [(team, points, gd), ...] sorted by standing.
    """
    n = len(teams)
    points = [0] * n
    gd = [0.0] * n
    gf = [0] * n

    for i, j in combinations(range(n), 2):
        ra, rb, ha = match_params[(i, j)]
        goals_a, goals_b = simulate_group_match(ra, rb, ha)

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

    order = sorted(
        range(n),
        key=lambda x: (points[x], gd[x], gf[x], random.random()),
        reverse=True,
    )
    return [(teams[idx], points[idx], gd[idx]) for idx in order]


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
    qualifying_thirds: list[tuple[str, str, int, float]],
) -> dict[int, str]:
    """Assign 8 qualifying 3rd-place teams to bracket slots.

    qualifying_thirds: [(team_name, group_letter, points, gd), ...]
    Returns: {slot_index: team_name} for the 8 THIRD_PLACE_SLOTS.
    """
    # Sort by group letter for consistent allocation
    by_group = {g: team for team, g, _, _ in qualifying_thirds}
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
    ratings: dict[str, float], n_sims: int = 50000
) -> dict[str, dict]:
    """Run full tournament Monte Carlo simulation.

    Returns per-team dict with counts for each round reached.
    """
    # Pre-compute group match probabilities
    group_params = {}
    for g, teams in GROUPS_2026.items():
        group_params[g] = _precompute_group_params(teams, ratings)

    # Initialize counters
    all_teams = []
    for teams in GROUPS_2026.values():
        all_teams.extend(teams)

    counts = {
        team: {"gs": 0, "r32": 0, "r16": 0, "qf": 0, "sf": 0, "final": 0, "winner": 0}
        for team in all_teams
    }
    # Also track group finishing position
    pos_counts = {team: [0, 0, 0, 0] for team in all_teams}

    for _ in range(n_sims):
        # 1. Simulate all groups
        standings = {}  # group -> [(team, pts, gd), ...]
        for g, teams in GROUPS_2026.items():
            standings[g] = simulate_group_once(teams, group_params[g])

        # Record group positions
        for g, standing in standings.items():
            for pos, (team, pts, gd) in enumerate(standing):
                pos_counts[team][pos] += 1

        # 2. Determine R32 qualifiers
        # 1st and 2nd from each group
        group_1st = {g: s[0][0] for g, s in standings.items()}
        group_2nd = {g: s[1][0] for g, s in standings.items()}

        # 3rd place: rank all 12, take best 8
        thirds = []
        for g, s in standings.items():
            team, pts, gd = s[2]
            thirds.append((team, g, pts, gd))
        thirds.sort(key=lambda x: (x[2], x[3], random.random()), reverse=True)
        qualifying_thirds = thirds[:8]

        # All R32 qualifiers advance
        r32_teams = set()
        for t in group_1st.values():
            r32_teams.add(t)
        for t in group_2nd.values():
            r32_teams.add(t)
        for t, _, _, _ in qualifying_thirds:
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
                w = simulate_knockout_match(
                    ratings.get(team_a, 1500), ratings.get(team_b, 1500),
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


def export_worldcup_json(elo: EloSystem, output_dir: Path) -> None:
    """Export World Cup 2026 predictions as JSON."""
    random.seed(2026)

    # Get all ratings
    all_ratings = {}
    for teams in GROUPS_2026.values():
        for t in teams:
            all_ratings[t] = elo.get_rating(t)

    # Run full tournament simulation
    sim_results = simulate_tournament(all_ratings, n_sims=10000)

    # Build per-group data (match probabilities for display)
    groups = {}
    for group_name, teams in GROUPS_2026.items():
        team_ratings = {t: all_ratings[t] for t in teams}

        # Match probabilities ordered by schedule
        matches = []
        schedule = MATCH_SCHEDULE.get(group_name, [])
        for i, j, date, venue in schedule:
            team_a, team_b = teams[i], teams[j]
            is_neutral = team_a not in HOST_NATIONS and team_b not in HOST_NATIONS
            home = team_a if team_a in HOST_NATIONS else (
                team_b if team_b in HOST_NATIONS else ""
            )
            if home == team_b:
                pa, pd, pb = match_probabilities(
                    team_ratings[team_b], team_ratings[team_a],
                    home_team=team_b, neutral=False,
                )
                matches.append({
                    "home": team_b, "away": team_a,
                    "p_home": round(pa * 100, 1),
                    "p_draw": round(pd * 100, 1),
                    "p_away": round(pb * 100, 1),
                    "is_neutral": False,
                    "date": date, "venue": venue,
                })
            else:
                pa, pd, pb = match_probabilities(
                    team_ratings[team_a], team_ratings[team_b],
                    home_team=home, neutral=is_neutral,
                )
                matches.append({
                    "home": team_a, "away": team_b,
                    "p_home": round(pa * 100, 1),
                    "p_draw": round(pd * 100, 1),
                    "p_away": round(pb * 100, 1),
                    "is_neutral": is_neutral,
                    "date": date, "venue": venue,
                })

        team_list = []
        for t in teams:
            team_list.append({
                "team": t,
                "slug": slugify(t),
                "rating": round(all_ratings[t], 0),
                **sim_results[t],
            })
        team_list.sort(key=lambda x: x["p_1st"], reverse=True)

        groups[group_name] = {"teams": team_list, "matches": matches}

    data = {"tournament": "2026 FIFA World Cup", "groups": groups}
    (output_dir / "worldcup2026.json").write_text(
        json.dumps(data, separators=(",", ":")), encoding="utf-8"
    )
