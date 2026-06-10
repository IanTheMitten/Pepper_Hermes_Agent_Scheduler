from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator

from pepper.domain.item import Commitment, Divisibility, Stakes
from pepper.time_util import duration_minutes, parse_iso


class AddEventInput(BaseModel):
    title: str = Field(min_length=1)
    start_time: str
    end_time: str
    location: str | None = None
    commitment: Commitment = Commitment.solo
    counterparty_id: int | None = None
    stakes: Stakes = Stakes.reschedulable
    type_id: int | None = None

    @field_validator("start_time", "end_time")
    @classmethod
    def _valid_iso(cls, v: str) -> str:
        parse_iso(v)
        return v

    @model_validator(mode="after")
    def _ordered(self) -> "AddEventInput":
        if duration_minutes(self.start_time, self.end_time) <= 0:
            raise ValueError("end_time must be after start_time")
        return self


class AddTaskInput(BaseModel):
    title: str = Field(min_length=1)
    duration_estimate: int = Field(gt=0)
    deadline: str | None = None
    divisibility: Divisibility = Divisibility.atomic
    stakes: Stakes = Stakes.reschedulable
    type_id: int | None = None

    @field_validator("deadline")
    @classmethod
    def _valid_iso(cls, v: str | None) -> str | None:
        if v is not None:
            parse_iso(v)
        return v


class GetScheduleInput(BaseModel):
    start_time: str
    end_time: str

    @field_validator("start_time", "end_time")
    @classmethod
    def _valid_iso(cls, v: str) -> str:
        parse_iso(v)
        return v
