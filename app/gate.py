"""The gate. Pure and deterministic: no model, no clock, no I/O.

Everything the language model produced arrives here as an Action and leaves as a
Decision. There is no third outcome.
"""

from app.schema import Action, Decision, Status


def decide(
    action: Action, state: dict, actions: dict[str, dict], procedure: dict
) -> Decision:
    if action.part is None:
        return _refuse(action, "AMBIGUOUS_REFERENCE", "which part do you mean?")

    spec = actions.get(f"{action.verb}|{action.part}")
    if spec is None:
        return _refuse(
            action, "UNKNOWN_PART", f"'{action.part}' is not a part on this twin"
        )

    if not spec.get("mutates", True):
        return _admit(action, "READ_ONLY_OK", spec.get("admit", "read-only view"))

    for flag in spec.get("requires", []):
        if not state.get(flag):
            return _refuse(action, "NOT_READY", spec["blocked"][flag])

    allowed = spec.get("procedure_steps", [])
    step = state["step"]
    if allowed and step not in allowed:
        return _refuse(
            action,
            "OUT_OF_SEQUENCE",
            f"procedure is at step {step} ({procedure['steps'][step]}); this action is step {allowed[0]}",
        )

    return _admit(action, "OK", spec.get("admit", "admitted"))


def _refuse(action: Action, code: str, message: str) -> Decision:
    return Decision(status=Status.REFUSE, code=code, message=message, action=action)


def _admit(action: Action, code: str, message: str) -> Decision:
    return Decision(status=Status.ADMIT, code=code, message=message, action=action)
