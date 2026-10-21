"""Runs one recorded parse through all three approaches and prints the table in the README.

The parse is an input, not part of the comparison: the same recorded LLM output goes to
every arm, so the only thing that differs between columns is the validation.
"""

import csv
from pathlib import Path

from app.approaches import context_gate, llm_only, manual_check
from app.policy import load_actions, load_manual
from app.schema import Action, Status
from app.twin import Twin, load_hierarchy

ROWS = Path(__file__).resolve().parent / "commands.csv"
ARMS = [
    ("llm only", llm_only.decide),
    ("manual check (2023)", manual_check.decide),
    ("context gate (2026)", context_gate.decide),
]


def parse(cell: str) -> Action:
    verb, _, part = cell.partition("|")
    return Action(verb=verb or "unknown", part=part or None)


def run(
    decide, row: dict, actions: dict, steps: dict, tree: dict
) -> tuple[str, bool, bool]:
    """(kind, admitted, executed) — executed means a mutating effect was applied."""
    twin = Twin(step=int(row["step"]), state=set(filter(None, row["state"].split(";"))))
    action = parse(row["llm_output"])
    decision = decide(action=action, twin=twin, actions=actions, steps=steps, tree=tree)
    spec = actions.get(f"{action.verb}|{action.part}")
    executed = (
        decision.status is Status.ADMIT and bool(spec) and spec.get("mutates", True)
    )
    if executed:
        twin.apply(action, spec)
    return row["kind"], decision.status is Status.ADMIT, executed


def main() -> None:
    rows = list(csv.DictReader(ROWS.open(encoding="utf-8")))
    actions, steps, tree = load_actions(), load_manual(), load_hierarchy()

    print(
        f"{'arm':22} {'unsafe executed':>16} {'safe admitted':>15} {'control refused':>16}"
    )
    print("-" * 71)
    for name, decide in ARMS:
        tally = {"unsafe": [0, 0], "safe": [0, 0], "control": [0, 0]}
        for row in rows:
            kind, admitted, executed = run(decide, row, actions, steps, tree)
            tally[kind][1] += 1
            if kind == "unsafe" and executed:
                tally["unsafe"][0] += 1
            elif kind == "safe" and admitted:
                tally["safe"][0] += 1
            elif kind == "control" and not admitted:
                tally["control"][0] += 1
        print(
            f"{name:22} {tally['unsafe'][0]:>8}/{tally['unsafe'][1]:<7} "
            f"{tally['safe'][0]:>7}/{tally['safe'][1]:<7} "
            f"{tally['control'][0]:>8}/{tally['control'][1]:<7}"
        )


if __name__ == "__main__":
    main()
