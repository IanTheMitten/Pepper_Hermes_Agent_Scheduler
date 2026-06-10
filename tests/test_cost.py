from pepper.cascade.cost import LEVER_PENALTY, drop_cost, move_cost


def test_lever_hierarchy_is_ordered():
    order = ["absorb", "compress", "shift", "split", "reorder", "drop"]
    penalties = [LEVER_PENALTY[k] for k in order]
    assert penalties == sorted(penalties)


def test_high_protection_costs_more_to_touch():
    assert move_cost(0.9, "shift") > move_cost(0.2, "shift")


def test_dropping_costs_more_than_compressing_same_item():
    assert drop_cost(0.5) > move_cost(0.5, "compress")
