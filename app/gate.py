"""The gate of the 2026 approach: what the twin currently is, not just what the manual says.

Pure and deterministic: no model, no clock, no I/O. The hierarchy and manual checks that
run before this one live in app/approaches/context_gate.py.
"""

from app.schema import Action, Decision, Status


def check_state(
    action: Action, twin, actions: dict[str, dict], steps: dict[int, str]
) -> Decision:
    spec = actions[f"{action.verb}|{action.part}"]

    for flag in spec.get("requires", []):
        if flag not in twin.state:
            return _refuse(action, "NOT_READY", spec["blocked"][flag])

    allowed = spec.get("procedure_steps", [])
    if allowed and twin.step not in allowed:
        return _refuse(
            action,
            "OUT_OF_SEQUENCE",
            f"procedure is at step {twin.step} ({steps[twin.step]}); this action is step {allowed[0]}",
        )

    return Decision(
        status=Status.ADMIT,
        code="OK",
        message=spec.get("admit", "admitted"),
        action=action,
    )


def refuse(action: Action, code: str, message: str) -> Decision:
    return Decision(status=Status.REFUSE, code=code, message=message, action=action)


def _refuse(action: Action, code: str, message: str) -> Decision:
    return refuse(action, code, message)
