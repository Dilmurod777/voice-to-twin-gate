from enum import StrEnum

from pydantic import BaseModel


class Status(StrEnum):
    ADMIT = "ADMIT"
    REFUSE = "REFUSE"


class Action(BaseModel):
    """What the language model claims it heard. Nothing here is trusted."""

    verb: str
    part: str | None = None


class Decision(BaseModel):
    status: Status
    code: str
    message: str
    action: Action
