from __future__ import annotations

import calendar
from datetime import date, timedelta

_WEEKDAYS = {"MO": 0, "TU": 1, "WE": 2, "TH": 3, "FR": 4, "SA": 5, "SU": 6}


def expand(freq: str, interval: int, byday: str | None, start: date, horizon_days: int,
           until: date | None) -> list[date]:
    end = start + timedelta(days=horizon_days)
    if until is not None:
        end = min(end, until)
    out: list[date] = []
    if freq == "daily":
        d = start
        while d <= end:
            out.append(d)
            d += timedelta(days=interval)
    elif freq == "weekly":
        wanted = {_WEEKDAYS[x] for x in byday.split(",")} if byday else {start.weekday()}
        d = start
        while d <= end:
            # Year-safe week delta: count whole 7-day spans from start so the
            # interval check never resets at year boundaries (unlike ISO week numbers).
            if d.weekday() in wanted and ((d - start).days // 7) % interval == 0:
                out.append(d)
            d += timedelta(days=1)
    elif freq == "monthly":
        # Step month-by-month (honoring `interval`) from the start month. The
        # instance day is the anchor day clamped to the month's length, so a
        # day-31 series lands on Feb 28/29, Apr 30, etc. The anchor day is never
        # mutated: Jan 31 -> Feb 28 -> Mar 31. Dates are strictly increasing as
        # the month advances, so the first date past `end` ends the series.
        anchor_day = start.day
        y, m = start.year, start.month
        while True:
            days_in_month = calendar.monthrange(y, m)[1]
            d = date(y, m, min(anchor_day, days_in_month))
            if d > end:
                break
            out.append(d)
            m += interval
            y += (m - 1) // 12
            m = (m - 1) % 12 + 1
    return out
