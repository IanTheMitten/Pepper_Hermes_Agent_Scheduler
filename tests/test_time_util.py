import pytest

from pepper.time_util import duration_minutes, overlaps, parse_iso, to_iso


def test_parse_iso_assigns_utc_when_naive():
    dt = parse_iso("2026-06-07T09:00:00")
    assert dt.utcoffset().total_seconds() == 0


def test_parse_iso_preserves_offset():
    dt = parse_iso("2026-06-07T09:00:00+09:00")
    assert dt.utcoffset().total_seconds() == 9 * 3600


def test_to_iso_roundtrips():
    assert to_iso(parse_iso("2026-06-07T09:00:00+00:00")) == "2026-06-07T09:00:00+00:00"


def test_duration_minutes():
    assert duration_minutes("2026-06-07T09:00:00", "2026-06-07T09:30:00") == 30


def test_overlaps_true_and_false():
    a = ("2026-06-07T09:00:00", "2026-06-07T10:00:00")
    assert overlaps(*a, "2026-06-07T09:30:00", "2026-06-07T11:00:00") is True
    assert overlaps(*a, "2026-06-07T10:00:00", "2026-06-07T11:00:00") is False


def test_parse_iso_rejects_garbage():
    with pytest.raises(ValueError):
        parse_iso("not-a-time")
