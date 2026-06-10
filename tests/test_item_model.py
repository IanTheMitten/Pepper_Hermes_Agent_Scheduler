import sqlite3

from pepper.domain.item import Commitment, Item, ItemStatus


def test_enum_values_are_plain_strings():
    assert Commitment.promise_to_others == "promise_to_others"
    assert ItemStatus.scheduled.value == "scheduled"


def test_item_from_row_maps_columns():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT 7 AS id, 'Standup' AS title, '2026-06-07T09:00:00+00:00' AS start_time, "
        "'2026-06-07T09:30:00+00:00' AS end_time, 30 AS duration_estimate, "
        "30 AS min_duration, 'Office' AS location, 'scheduled' AS status, "
        "NULL AS type_id, 'solo' AS commitment, NULL AS counterparty_id, "
        "'fixed_time' AS temporal_class, NULL AS deadline, 'reschedulable' AS stakes, "
        "'atomic' AS divisibility, NULL AS rigidity_score, NULL AS protection_score, "
        "NULL AS goal_id, NULL AS effort_estimate, NULL AS project_id, 0 AS auto_reserved, "
        "NULL AS parent_item_id, NULL AS series_id, 0 AS detached, "
        "1 AS version, 'c' AS created_at, 'u' AS updated_at"
    ).fetchone()

    item = Item.from_row(row)

    assert item.id == 7
    assert item.title == "Standup"
    assert item.duration_estimate == 30
    assert item.temporal_class == "fixed_time"
    assert item.protection_score is None
    assert item.detached == 0
    assert item.version == 1
