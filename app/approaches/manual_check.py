"""The 2023 framework: generate the symbols, then check them against the manual.

It knows the manual's words and its order. It knows nothing about the aircraft: not what
is pressurised, not what is behind a closed panel, not whether a part exists at all. That
is the gap the 2026 approach is about.
"""

import re

from app.gate import refuse
from app.schema import Action, Decision, Status


def _tokens(text: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", text.lower()) if w}


def best_step(action: Action, steps: dict[int, str]) -> int | None:
    """The step whose wording overlaps the command most, among steps that use its verb.

    Requiring the verb keeps "fit a new filter" out of the "remove the filter" step; the
    remaining overlap then separates "open the panel" from "open the valve".
    """
    words = _tokens(action.verb) | _tokens(action.part or "")
    head = action.verb.split("_")[0].lower()
    candidates = [
        (len(words & _tokens(text)), n)
        for n, text in steps.items()
        if head in _tokens(text)
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda pair: (pair[0], -pair[1]))[1]


def decide(action: Action, twin, steps: dict[int, str], **_):
    if action.part is None:
        return refuse(action, "AMBIGUOUS_REFERENCE", "which part do you mean?")

    step = best_step(action, steps)
    if step is None:
        return refuse(
            action,
            "NOT_IN_MANUAL",
            f"the manual has no instruction for '{action.verb} {action.part}'",
        )
    if step != twin.step:
        return refuse(
            action,
            "OUT_OF_SEQUENCE",
            f"manual is at step {twin.step}; that instruction is step {step}",
        )

    return Decision(
        status=Status.ADMIT,
        code="OK",
        message=f"matches manual step {step}",
        action=action,
    )
