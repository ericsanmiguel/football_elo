"""Tests for FIFA's fixed third-place allocation in the 2026 Round of 32.

Locks in that ``allocate_third_place`` follows the official Annex C table
(third_place_allocation), not an ad-hoc rematch-avoiding heuristic.
"""

import itertools

from football_elo.third_place_allocation import (
    THIRD_PLACE_ALLOCATION,
    WINNER_GROUPS,
    assign_third_places,
)
from football_elo.worldcup import (
    THIRD_PLACE_SLOTS,
    THIRD_PLACE_SLOT_WINNERS,
    allocate_third_place,
)

ALL_GROUPS = "ABCDEFGHIJKL"


def _thirds(groups):
    # (team_name, group, pts, gd, gf); points/gd/gf are irrelevant to allocation.
    return [(f"third_{g}", g, 3, 0, 0) for g in groups]


def test_table_is_complete_and_consistent():
    assert len(THIRD_PLACE_ALLOCATION) == 495  # C(12, 8)
    for key, code in THIRD_PLACE_ALLOCATION.items():
        assert len(key) == 8 and len(code) == 8
        assert set(code) == set(key)                 # bijection onto advancing set
        for winner, third in zip(WINNER_GROUPS, code):
            assert winner != third                   # no same-group rematch


def test_known_combination_matches_official_table():
    # Thirds advancing from E,F,G,H,I,J,K,L -> documented FIFA assignment.
    assignment = allocate_third_place(_thirds("EFGHIJKL"))
    # slot -> winner group -> third group -> "third_<group>"
    expected_third_group = {"E": "F", "I": "G", "A": "E", "L": "K",
                            "D": "I", "G": "H", "B": "J", "K": "L"}
    expected = {
        slot: f"third_{expected_third_group[w]}"
        for slot, w in zip(THIRD_PLACE_SLOTS, THIRD_PLACE_SLOT_WINNERS)
    }
    assert assignment == expected


def test_every_combination_is_a_valid_no_rematch_assignment():
    slot_winner = dict(zip(THIRD_PLACE_SLOTS, THIRD_PLACE_SLOT_WINNERS))
    for groups in itertools.combinations(ALL_GROUPS, 8):
        assignment = allocate_third_place(_thirds(groups))
        # Each of the eight qualifying thirds is placed exactly once.
        assert sorted(assignment.values()) == sorted(f"third_{g}" for g in groups)
        # A winner never faces the third-placed team from its own group.
        for slot, team in assignment.items():
            assert team != f"third_{slot_winner[slot]}"


def test_assign_third_places_rejects_wrong_size():
    import pytest
    with pytest.raises(KeyError):
        assign_third_places(set("ABCDEFG"))   # only 7 groups
