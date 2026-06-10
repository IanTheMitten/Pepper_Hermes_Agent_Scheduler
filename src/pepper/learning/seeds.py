from __future__ import annotations

# Community-maintainable cold-start library. Each seed is a low-confidence default;
# the first real observations override it (see learning_service.recompute).
SEED_LIBRARY: dict[str, dict] = {
    "standup": {"duration": 30, "buffer": 5, "divisibility": "atomic", "commitment": "promise_to_others"},
    "1:1": {"duration": 30, "buffer": 5, "divisibility": "atomic", "commitment": "promise_to_others"},
    "lunch": {"duration": 60, "buffer": 10, "divisibility": "atomic", "commitment": "solo"},
    "commute": {"duration": 25, "buffer": 0, "divisibility": "atomic", "commitment": "solo"},
    "gym": {"duration": 60, "buffer": 10, "divisibility": "atomic", "commitment": "promise_to_self"},
    "deep_work": {"duration": 90, "buffer": 10, "divisibility": "divisible", "commitment": "promise_to_self"},
    "doctor": {"duration": 45, "buffer": 15, "divisibility": "atomic", "commitment": "promise_to_others"},
}


def seed_estimate(type_name: str) -> dict | None:
    return SEED_LIBRARY.get(type_name)
