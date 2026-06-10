import pytest

from pepper.integration import hermes


def test_fakes_record_calls():
    gw = hermes.FakeGateway()
    gw.send("leave now")
    assert gw.sent == ["leave now"]
    cron = hermes.FakeCron()
    cron.schedule("r-1", "2026-06-09T08:55:00+00:00", {"item_id": 1})
    assert cron.jobs[0][0] == "r-1"
    mem = hermes.FakeMemory({"day_bounds": {"wake": "07:00"}})
    assert mem.query("day_bounds") == {"wake": "07:00"}
    assert mem.query("missing") is None


def test_registry_round_trips():
    gw = hermes.FakeGateway()
    hermes.set_gateway(gw)
    hermes.get_gateway().send("x")
    assert gw.sent == ["x"]
    hermes.reset()
    with pytest.raises(RuntimeError):
        hermes.get_gateway()  # unwired -> explicit error, never a silent no-op
