"""The 2026 approach: the manual is necessary and not sufficient.

Order matters, and each layer answers a different question:
  1. intent    — is this a view? then it is always allowed and changes nothing.
  2. spatial   — does the part exist in the twin's hierarchy, and is it reachable now?
  3. procedural — does the manual have this instruction at this step? (the 2023 layer)
  4. state     — is the aircraft actually ready for it?
"""

from app.approaches import manual_check
from app.gate import check_state, refuse
from app.schema import Action, Decision, Status
from app.twin import reachable


def decide(
    action: Action, twin, actions: dict, steps: dict[int, str], tree: dict
) -> Decision:
    if action.part is None:
        return refuse(action, "AMBIGUOUS_REFERENCE", "which part do you mean?")

    spec = actions.get(f"{action.verb}|{action.part}")
    if spec is not None and not spec.get("mutates", True):
        return Decision(
            status=Status.ADMIT,
            code="READ_ONLY_OK",
            message=spec.get("admit", "read-only view"),
            action=action,
        )

    ok, why = reachable(action.part, tree, twin.state)
    if not ok:
        return refuse(
            action, "UNKNOWN_PART" if "hierarchy" in why else "NOT_ACCESSIBLE", why
        )

    if spec is None:
        return refuse(
            action,
            "UNKNOWN_PART",
            f"the twin has no action for '{action.verb} {action.part}'",
        )

    if spec.get("manual") is False:
        return Decision(
            status=Status.ADMIT,
            code="HOUSEKEEPING",
            message=spec.get("admit", "not a procedure step"),
            action=action,
        )

    checked = manual_check.decide(action, twin, steps)
    if checked.status is Status.REFUSE:
        return checked

    return check_state(action, twin, actions, steps)
