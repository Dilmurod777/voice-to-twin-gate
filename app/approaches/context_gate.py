"""The 2026 approach: the manual is necessary and not sufficient.

Order matters, and each layer answers a different question:
  1. intent    — is this a view? then it is always allowed and changes nothing.
  2. spatial   — does the part exist in the twin's hierarchy, and is it reachable now?
  3. procedural — does the manual have this instruction at this step? (the 2023 layer)
  4. state     — is the aircraft actually ready for it?

Every layer reports what it produced and what it cost, so the page can show the pipeline
rather than describe it.
"""

from time import perf_counter

from app.approaches import manual_check
from app.gate import check_state, refuse
from app.schema import Action, Decision, Status, Step
from app.twin import blocker as blocking_door
from app.twin import reachable, trail


def decide(
    action: Action, twin, actions: dict, steps: dict[int, str], tree: dict
) -> Decision:
    if action.part is None:
        return done(
            refuse(action, "AMBIGUOUS_REFERENCE", "which part do you mean?"),
            [Step(stage="hierarchy", value="no part to look up", state="fail")],
        )

    spec = actions.get(f"{action.verb}|{action.part}")
    if spec is not None and not spec.get("mutates", True):
        return done(
            Decision(
                status=Status.ADMIT,
                code="READ_ONLY_OK",
                message=spec.get("admit", "read-only view"),
                action=action,
            ),
            [Step(stage="intent", value="view only, nothing to check")],
        )

    started = perf_counter()
    ok, why = reachable(action.part, tree, twin.state)
    spatial = Step(
        stage="hierarchy",
        value=" › ".join(trail(action.part, tree)) if ok else why,
        state="pass" if ok else "fail",
        ms=round((perf_counter() - started) * 1000, 3),
    )
    if not ok:
        return done(
            refuse(
                action,
                "UNKNOWN_PART" if "hierarchy" in why else "NOT_ACCESSIBLE",
                why,
                blocking_door(action.part, tree, twin.state),
            ),
            [spatial],
        )

    if spec is None:
        return done(
            refuse(
                action,
                "UNKNOWN_PART",
                f"the twin has no action for '{action.verb} {action.part}'",
            ),
            [spatial],
        )

    started = perf_counter()
    step = manual_check.best_step(action, steps)
    procedural = Step(
        stage="manual",
        value=f"step {step}" if step else "no instruction",
        state="pass" if step == twin.step else "fail",
        ms=round((perf_counter() - started) * 1000, 3),
    )
    trace = [spatial, procedural]
    if step is None:
        return done(
            refuse(
                action,
                "NOT_IN_MANUAL",
                f"the manual has no instruction for '{action.verb} {action.part}'",
            ),
            trace,
        )
    if step != twin.step:
        return done(
            refuse(
                action,
                "OUT_OF_SEQUENCE",
                f"manual is at step {twin.step}; that instruction is step {step}",
            ),
            trace,
        )

    started = perf_counter()
    decision = check_state(action, twin, actions, steps)
    trace.append(
        Step(
            stage="state",
            value="preconditions hold"
            if decision.status is Status.ADMIT
            else decision.message,
            state="pass" if decision.status is Status.ADMIT else "fail",
            ms=round((perf_counter() - started) * 1000, 3),
        )
    )
    return done(decision, trace)


def done(decision: Decision, trace: list[Step]) -> Decision:
    decision.trace = trace
    return decision
