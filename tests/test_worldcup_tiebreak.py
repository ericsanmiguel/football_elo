"""Tests for the 2026 World Cup group tie-breaking rules.

For teams level on points, FIFA's 2026 rules apply head-to-head record
(points, goal difference, goals scored among the tied teams) BEFORE overall
goal difference — a change from earlier tournaments. These tests pin that
ordering down on the pure ranking helper.
"""

from football_elo.worldcup import _rank_group


def test_head_to_head_beats_overall_goal_difference():
    # Teams 0 and 1 both finish on 6 points. Team 1 has the better overall
    # goal difference, but Team 0 won their head-to-head meeting. Under the
    # 2026 rules head-to-head wins, so Team 0 must rank above Team 1.
    points = [6, 6, 3, 0]
    gd = [4, 6, 0, -10]          # team 1 better overall GD
    gf = [5, 8, 3, 1]
    played = {
        (0, 1): (1, 0),          # team 0 beat team 1 head-to-head
        (0, 2): (2, 1),
        (0, 3): (2, 0),
        (1, 2): (3, 0),
        (1, 3): (5, 0),
        (2, 3): (1, 0),
    }
    order = _rank_group(4, points, gd, gf, played, rand_keys=[0, 0, 0, 0])
    assert order.index(0) < order.index(1)


def test_drawn_head_to_head_falls_through_to_overall_gd():
    # Teams 0 and 1 level on points and drew their meeting, so head-to-head
    # cannot separate them: overall goal difference decides, favouring 1.
    points = [6, 6, 3, 0]
    gd = [2, 5, 0, -7]
    gf = [4, 7, 3, 1]
    played = {
        (0, 1): (1, 1),          # draw — no head-to-head separation
        (0, 2): (1, 0),
        (0, 3): (2, 1),
        (1, 2): (2, 0),
        (1, 3): (4, 0),
        (2, 3): (1, 0),
    }
    order = _rank_group(4, points, gd, gf, played, rand_keys=[0, 0, 0, 0])
    assert order.index(1) < order.index(0)


def test_three_way_tie_resolved_by_head_to_head_minitable():
    # Teams 0, 1, 2 all finish on 6 points in a head-to-head cycle
    # (0>1, 1>2, 2>0) with differing margins. The mini-table goal difference
    # orders them 2, 1, 0 regardless of overall GD, which is set to mislead.
    points = [6, 6, 6, 0]
    gd = [99, 0, -99, -50]       # overall GD deliberately favours team 0
    gf = [99, 5, 1, 0]
    played = {
        (0, 1): (1, 0),          # 0 beats 1 by 1
        (1, 2): (1, 0),          # 1 beats 2 by 1
        (0, 2): (0, 2),          # 2 beats 0 by 2
        (0, 3): (1, 0),
        (1, 3): (1, 0),
        (2, 3): (1, 0),
    }
    order = _rank_group(4, points, gd, gf, played, rand_keys=[0, 0, 0, 0])
    assert order[:3] == [2, 1, 0]
