from enum import StrEnum

from pydantic import BaseModel, Field


class Status(StrEnum):
    ADMIT = "ADMIT"
    REFUSE = "REFUSE"


class Action(BaseModel):
    """What the language model claims it heard. Nothing here is trusted."""

    verb: str
    part: str | None = None


class Step(BaseModel):
    """One component of an arm, with what it produced and what it cost."""

    stage: str
    value: str
    state: str = "pass"
    ms: float = 0.0


class Decision(BaseModel):
    status: Status
    code: str
    message: str
    action: Action
    blocker: str | None = None
    trace: list[Step] = Field(default_factory=list)
