from datetime import date

from pepper.recurrence.expand import expand


def test_daily_expands_each_day():
    days = expand("daily", 1, None, date(2026, 6, 8), horizon_days=4, until=None)
    assert days == [date(2026, 6, 8), date(2026, 6, 9), date(2026, 6, 10),
                    date(2026, 6, 11), date(2026, 6, 12)]


def test_weekly_byday_filters_weekdays():
    days = expand("weekly", 1, "MO,WE,FR", date(2026, 6, 8), horizon_days=6, until=None)
    # Mon 8, Wed 10, Fri 12
    assert days == [date(2026, 6, 8), date(2026, 6, 10), date(2026, 6, 12)]


def test_weekly_interval_two_crosses_year():
    # 2026-12-28 is a Monday; biweekly MO must use a year-safe week delta so the
    # series stays on every-other-Monday across the 2026->2027 boundary.
    days = expand("weekly", 2, "MO", date(2026, 12, 28), horizon_days=35, until=None)
    assert days == [date(2026, 12, 28), date(2027, 1, 11), date(2027, 1, 25)]


def test_until_caps_the_series():
    days = expand("daily", 1, None, date(2026, 6, 8), horizon_days=30, until=date(2026, 6, 9))
    assert days == [date(2026, 6, 8), date(2026, 6, 9)]


def test_monthly_clamps_day_31_across_a_year_including_leap_february():
    # Anchored on the 31st: each month emits min(31, days_in_month). 2024 is a
    # leap year, so February clamps to the 29th. The anchor (31) is never mutated.
    days = expand("monthly", 1, None, date(2024, 1, 31), horizon_days=160, until=None)
    assert days == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31),
                    date(2024, 4, 30), date(2024, 5, 31), date(2024, 6, 30)]


def test_monthly_interval_two_is_bimonthly():
    # interval=2 must fire every other month, not every month.
    days = expand("monthly", 2, None, date(2026, 1, 15), horizon_days=365,
                  until=date(2026, 7, 31))
    assert days == [date(2026, 1, 15), date(2026, 3, 15), date(2026, 5, 15),
                    date(2026, 7, 15)]


def test_monthly_interval_twelve_yearly_clamps_leap_february():
    # interval=12 is a yearly series. Anchored Feb 29 2024 (leap), the next
    # instance clamps to Feb 28 2025 (non-leap), proving the anchor day is held.
    days = expand("monthly", 12, None, date(2024, 2, 29), horizon_days=800, until=None)
    assert days == [date(2024, 2, 29), date(2025, 2, 28), date(2026, 2, 28)]


def test_monthly_day_31_crosses_year_boundary():
    # A day-31 monthly series must step Dec -> Jan across the year boundary,
    # clamping each short month on the way.
    days = expand("monthly", 1, None, date(2025, 11, 30), horizon_days=120, until=None)
    assert days == [date(2025, 11, 30), date(2025, 12, 30), date(2026, 1, 30),
                    date(2026, 2, 28), date(2026, 3, 30)]
