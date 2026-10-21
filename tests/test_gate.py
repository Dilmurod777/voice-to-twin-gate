import pytest

from app.gate import decide
from app.policy import load_actions, load_procedure
from app.schema import Action, Status

ACTIONS = load_actions()
PROCEDURE = load_procedure()


def twin(step=1, **flags):
    """The twin's state at the start of the procedure: braked, closed, pressurised."""
    state = {
        "step": step,
        "parking_brake": True,
        "panel_open": False,
        "fuel_depressurised": False,
    }
    state.update(flags)
    return state


def test_panel_is_admitted_at_step_one():
    decision = decide(
        Action(verb="open_panel", part="access_panel"), twin(), ACTIONS, PROCEDURE
    )

    assert decision.status is Status.ADMIT
    assert decision.code == "OK"


def test_fuel_valve_is_refused_while_pressurised():
    decision = decide(
        Action(verb="open_valve", part="fuel_valve"), twin(step=3), ACTIONS, PROCEDURE
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "NOT_READY"
    assert decision.message == "fuel system is not depressurised"


def test_fuel_valve_is_admitted_once_depressurised():
    decision = decide(
        Action(verb="open_valve", part="fuel_valve"),
        twin(step=3, panel_open=True, fuel_depressurised=True),
        ACTIONS,
        PROCEDURE,
    )

    assert decision.status is Status.ADMIT


def test_pump_is_refused_out_of_sequence():
    # Every precondition is satisfied, so the only reason left is the step order.
    decision = decide(
        Action(verb="remove_pump", part="hydraulic_pump"),
        twin(step=2, panel_open=True),
        ACTIONS,
        PROCEDURE,
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "OUT_OF_SEQUENCE"
    assert "step 6" in decision.message


def test_inspection_is_admitted_at_any_step():
    decision = decide(
        Action(verb="inspect", part="landing_gear"), twin(step=4), ACTIONS, PROCEDURE
    )

    assert decision.status is Status.ADMIT
    assert decision.code == "READ_ONLY_OK"


def test_unknown_part_is_refused():
    decision = decide(
        Action(verb="open_panel", part="wing"), twin(), ACTIONS, PROCEDURE
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "UNKNOWN_PART"


def test_missing_part_is_refused_as_ambiguous():
    decision = decide(Action(verb="open_panel", part=None), twin(), ACTIONS, PROCEDURE)

    assert decision.status is Status.REFUSE
    assert decision.code == "AMBIGUOUS_REFERENCE"


@pytest.mark.parametrize("key", list(ACTIONS))
def test_every_requirement_has_a_message(key):
    spec = ACTIONS[key]
    assert set(spec.get("requires", [])) <= set(spec.get("blocked", {}))


def test_every_step_referenced_by_a_policy_row_exists():
    for spec in ACTIONS.values():
        for step in spec.get("procedure_steps", []):
            assert step in PROCEDURE["steps"]
