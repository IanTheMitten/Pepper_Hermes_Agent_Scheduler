from pepper.reminders.timing import lead_minutes, remind_at


def test_located_item_uses_travel_plus_prep():
    assert lead_minutes(located=True, travel=25, learned_slip=0, default_lead=5, prep=5) == 30


def test_unlocated_uses_default_plus_learned_slip():
    assert lead_minutes(located=False, travel=None, learned_slip=8, default_lead=5, prep=5) == 13


def test_per_item_override_wins():
    assert lead_minutes(located=True, travel=25, learned_slip=0, override=45) == 45


def test_remind_at_subtracts_lead():
    assert remind_at("2026-06-09T09:00:00+00:00", 30) == "2026-06-09T08:30:00+00:00"
