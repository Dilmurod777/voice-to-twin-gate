import pytest

from app.approaches import context_gate, llm_only, manual_check
from app.policy import load_actions, load_manual
from app.schema import Action, Status
from app.twin import Twin, load_hierarchy

ACTIONS = load_actions()
STEPS = load_manual()
TREE = load_hierarchy()


def twin(step=1, *flags):
    return Twin(step=step, state=set(flags))


def gate(action, twin_state):
    return context_gate.decide(
        action=action, twin=twin_state, actions=ACTIONS, steps=STEPS, tree=TREE
    )


# --- the 2023 arm ---------------------------------------------------------


def test_2023_admits_the_step_the_manual_is_on():
    decision = manual_check.decide(
        Action(verb="open_panel", part="access_panel"), twin(1), STEPS
    )

    assert decision.status is Status.ADMIT


def test_2023_refuses_a_later_step():
    decision = manual_check.decide(
        Action(verb="remove_pump", part="hydraulic_pump"), twin(2), STEPS
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "OUT_OF_SEQUENCE"


def test_2023_cannot_see_the_aircraft_state():
    # Right step, wrong aircraft: the system is still pressurised.
    decision = manual_check.decide(
        Action(verb="open_valve", part="fuel_valve"), twin(3), STEPS
    )

    assert decision.status is Status.ADMIT


def test_2023_refuses_a_legitimate_inspection():
    # The blind spot in the other direction: a view is not an instruction.
    decision = manual_check.decide(
        Action(verb="inspect", part="landing_gear"), twin(3), STEPS
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "NOT_IN_MANUAL"


def test_2023_is_fooled_by_the_manuals_own_words():
    # "wing root" is in step 1, so a nonsense command scores against it.
    decision = manual_check.decide(
        Action(verb="open_panel", part="wing"), twin(1), STEPS
    )

    assert decision.status is Status.ADMIT


# --- the 2026 arm --------------------------------------------------------


def test_gate_refuses_a_pressurised_valve():
    decision = gate(
        Action(verb="open_valve", part="fuel_valve"), twin(3, "access_panel_open")
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "NOT_READY"
    assert decision.message == "fuel system is not depressurised"


def test_gate_refuses_a_part_behind_a_closed_panel():
    decision = gate(
        Action(verb="remove_filter", part="fuel_filter"), twin(4, "fuel_depressurised")
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "NOT_ACCESSIBLE"
    assert "access panel 12A" in decision.message


def test_gate_admits_a_legitimate_inspection():
    decision = gate(
        Action(verb="inspect", part="landing_gear"), twin(3, "access_panel_open")
    )

    assert decision.status is Status.ADMIT
    assert decision.code == "READ_ONLY_OK"


def test_gate_refuses_a_part_that_is_not_in_the_twin():
    decision = gate(Action(verb="open_panel", part="wing"), twin(1))

    assert decision.status is Status.REFUSE
    assert decision.code == "UNKNOWN_PART"


# --- the three arms together --------------------------------------------


def test_llm_only_admits_everything_it_is_given():
    action = Action(verb="remove_pump", part="hydraulic_pump")

    assert llm_only.decide(action=action).status is Status.ADMIT


@pytest.mark.parametrize(
    "key", [k for k, v in ACTIONS.items() if v.get("mutates", True)]
)
def test_both_arms_agree_on_which_step_an_action_belongs_to(key):
    """The manual the 2023 arm reads and the policy the 2026 arm enforces must not drift."""
    spec = ACTIONS[key]
    action = Action(verb=spec["verb"], part=spec["part"])

    assert manual_check.best_step(action, STEPS) == spec["procedure_steps"][0]


@pytest.mark.parametrize("key", list(ACTIONS))
def test_every_action_has_a_home_in_the_hierarchy(key):
    spec = ACTIONS[key]

    assert spec["part"] in __import__("json").dumps(TREE)


@pytest.mark.parametrize(
    "key", [k for k, v in ACTIONS.items() if v.get("mutates", True)]
)
def test_every_mutating_action_declares_what_it_sets(key):
    assert ACTIONS[key]["sets"]


def test_gate_refuses_out_of_sequence():
    decision = gate(
        Action(verb="remove_pump", part="hydraulic_pump"), twin(2, "access_panel_open")
    )

    assert decision.status is Status.REFUSE
    assert decision.code == "OUT_OF_SEQUENCE"
