from pepper.integration import hermes
from pepper.repositories import person_repo
from pepper.services import onboarding_service


def test_build_plan_asks_only_the_gaps():
    mem = hermes.FakeMemory({"day_bounds": {"wake": "07:00", "work": "09:00-18:00"}})
    plan = onboarding_service.build_plan(mem)
    by_topic = {t.topic: t for t in plan}
    assert by_topic["daily_rhythm"].status == "prefilled"   # already in Hermes memory
    assert by_topic["hard_lines"].status == "ask"           # not in memory -> ask


def test_seed_persons_from_honcho(conn):
    mem = hermes.FakeMemory({"important_people": [
        {"name": "Sam", "relationship": "partner", "weight": "high"},
    ]})
    created = onboarding_service.seed_persons(conn, mem)
    assert created == 1
    pid = person_repo.find_by_name(conn, "Sam")[0]
    assert person_repo.get(conn, pid).counterparty_weight == "high"
