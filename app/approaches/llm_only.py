"""Baseline: whatever the language model produced is executed. No check at all.

This is not a strawman — it is what an unconstrained voice assistant does, and it is the
arm the other two have to beat.
"""

from time import perf_counter

from app.schema import Action, Decision, Status, Step


def decide(action: Action, **_):
    started = perf_counter()
    trace = [
        Step(
            stage="execute",
            value=f"{action.verb}({action.part or '—'})",
            ms=round((perf_counter() - started) * 1000, 3),
        )
    ]
    return Decision(
        status=Status.ADMIT,
        code="LLM_TRUSTED",
        message=f"executed {action.verb} {action.part or ''}".strip(),
        action=action,
        trace=trace,
    )
