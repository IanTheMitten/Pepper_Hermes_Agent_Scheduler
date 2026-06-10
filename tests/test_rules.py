from pepper.repositories import rule_repo
from pepper.rules import engine


def test_no_before_rule_lifts_earliest_minute(conn):
    rule_repo.add(conn, kind="no_before", target_type_id=None, param="09:00")
    # earliest for a block defaults to 480 (08:00); the rule pushes it to 540 (09:00)
    assert engine.earliest_floor(conn, type_id=None) == 540


def test_cost_bias_rule_contributes_a_bounded_modifier(conn):
    t = 1
    rule_repo.add(conn, kind="cost_bias", target_type_id=t, param="1.2")
    mods = engine.cost_modifiers(conn, type_id=t)
    assert mods == [1.2]
    assert engine.cost_modifiers(conn, type_id=999) == []
