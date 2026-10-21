"""Baseline: whatever the language model produced is executed. No check at all.

This is not a strawman — it is what an unconstrained voice assistant does, and it is the
arm the other two have to beat.
"""

from app.schema import Action, Decision, Status


def decide(action: Action, **_):
    return Decision(
        status=Status.ADMIT,
        code="LLM_TRUSTED",
        message=f"executed {action.verb} {action.part or ''}".strip(),
        action=action,
    )
