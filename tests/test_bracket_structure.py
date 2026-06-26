"""The knockout bracket must reproduce FIFA's published 2026 tree.

The simulation advances winners by pairing consecutive R32_BRACKET entries
((0,1),(2,3),...) round after round, so R32_BRACKET must be laid out in
bracket-leaf order. This test pins the whole tree -- R32 leaves up through the
final -- against FIFA's official match numbering (M73-M104).
"""

from football_elo.worldcup import (
    R32_BRACKET,
    THIRD_PLACE_SLOTS,
    THIRD_PLACE_SLOT_WINNERS,
)

# Official R32 match definitions by (team_a_source, team_b_source). Each source
# pair is unique, so this maps an R32_BRACKET entry to its FIFA match number.
SOURCE_TO_MATCH = {
    ("2A", "2B"): 73, ("1E", "3"): 74, ("1F", "2C"): 75, ("1C", "2F"): 76,
    ("1I", "3"): 77, ("2E", "2I"): 78, ("1A", "3"): 79, ("1L", "3"): 80,
    ("1D", "3"): 81, ("1G", "3"): 82, ("2K", "2L"): 83, ("1H", "2J"): 84,
    ("1B", "3"): 85, ("1J", "2H"): 86, ("1K", "3"): 87, ("2D", "2G"): 88,
}

# FIFA's published feeders for each knockout match (from the official schedule).
FIFA_R16 = {89: (74, 77), 90: (73, 75), 91: (76, 78), 92: (79, 80),
            93: (83, 84), 94: (81, 82), 95: (86, 88), 96: (85, 87)}
FIFA_QF = {97: (89, 90), 98: (93, 94), 99: (91, 92), 100: (95, 96)}
FIFA_SF = {101: (97, 98), 102: (99, 100)}
FIFA_FINAL = {104: (101, 102)}


def _advance(prev_round_matches, fifa_round):
    """Pair consecutive matches and resolve each to its FIFA match number."""
    by_feeders = {frozenset(v): k for k, v in fifa_round.items()}
    out = []
    for i in range(0, len(prev_round_matches), 2):
        feeders = frozenset((prev_round_matches[i], prev_round_matches[i + 1]))
        assert feeders in by_feeders, f"no FIFA match is fed by {set(feeders)}"
        out.append(by_feeders[feeders])
    return out


def test_bracket_reproduces_fifa_tree():
    # Map the actual R32_BRACKET to FIFA match numbers in its laid-out order.
    leaves = [SOURCE_TO_MATCH[tuple(pair)] for pair in R32_BRACKET]
    assert len(leaves) == 16 and len(set(leaves)) == 16

    # Consecutive pairing, round by round, must walk FIFA's exact tree.
    r16 = _advance(leaves, FIFA_R16)
    qf = _advance(r16, FIFA_QF)
    sf = _advance(qf, FIFA_SF)
    final = _advance(sf, FIFA_FINAL)
    assert final == [104]


def test_third_place_slots_consistent_with_bracket():
    # THIRD_PLACE_SLOTS must be exactly the entries whose second source is "3",
    # and each slot's winner must match the listed group.
    derived = [i for i, (_a, b) in enumerate(R32_BRACKET) if b == "3"]
    assert derived == THIRD_PLACE_SLOTS
    for slot, winner in zip(THIRD_PLACE_SLOTS, THIRD_PLACE_SLOT_WINNERS):
        src_a, src_b = R32_BRACKET[slot]
        assert src_b == "3"
        assert src_a == f"1{winner}"
