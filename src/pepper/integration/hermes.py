from __future__ import annotations

from typing import Protocol


class HermesGateway(Protocol):
    def send(self, message: str) -> None: ...


class HermesCron(Protocol):
    def schedule(self, job_id: str, when_iso: str, payload: dict) -> None: ...


class HermesMemory(Protocol):
    def query(self, key: str) -> dict | None: ...


class FakeGateway:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def send(self, message: str) -> None:
        self.sent.append(message)


class FakeCron:
    def __init__(self) -> None:
        self.jobs: list[tuple[str, str, dict]] = []

    def schedule(self, job_id: str, when_iso: str, payload: dict) -> None:
        self.jobs.append((job_id, when_iso, payload))


class FakeMemory:
    def __init__(self, data: dict | None = None) -> None:
        self._data = data or {}

    def query(self, key: str) -> dict | None:
        return self._data.get(key)


_gateway: HermesGateway | None = None
_cron: HermesCron | None = None
_memory: HermesMemory | None = None


def set_gateway(g: HermesGateway) -> None:
    global _gateway
    _gateway = g


def set_cron(c: HermesCron) -> None:
    global _cron
    _cron = c


def set_memory(m: HermesMemory) -> None:
    global _memory
    _memory = m


def get_gateway() -> HermesGateway:
    if _gateway is None:
        raise RuntimeError("Hermes gateway not wired (call integration.hermes.set_gateway)")
    return _gateway


def get_cron() -> HermesCron:
    if _cron is None:
        raise RuntimeError("Hermes cron not wired")
    return _cron


def get_memory() -> HermesMemory:
    if _memory is None:
        raise RuntimeError("Hermes memory not wired")
    return _memory


def reset() -> None:
    global _gateway, _cron, _memory
    _gateway = _cron = _memory = None
