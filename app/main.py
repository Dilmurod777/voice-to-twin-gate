"""The demo server: one in-memory aircraft, three validators per command.

The gate is the system of record. The other two arms are counterfactuals on the same
state: they answer what would have happened, and the twin only moves when the gate says
so. Each arm also reports the state it would have left behind, so its 3D view can show
what it would have done rather than describe it.
"""

from pathlib import Path
from time import perf_counter

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.approaches import context_gate, llm_only, manual_check
from app.llm import parse
from app.policy import load_actions, load_manual
from app.schema import Action, Decision, Status
from app.twin import Twin, load_hierarchy, reachable, trail

WEB = Path(__file__).resolve().parent.parent / "web"
ACTIONS, STEPS, TREE = load_actions(), load_manual(), load_hierarchy()

ARMS = [
    ("LLM only", "executes the parse", llm_only.decide),
    ("Manual check · 2023", "the manual, and only the manual", manual_check.decide),
    ("Context gate · 2026", "manual + 3D hierarchy + state", context_gate.decide),
]


def label(node_id: str, tree: dict | None = None) -> str:
    tree = tree or TREE
    if tree["id"] == node_id:
        return tree["label"]
    for child in tree.get("children", []):
        found = label(node_id, child)
        if found:
            return found
    return ""


class Session:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.twin = Twin(step=1)

    def run(self, text: str) -> dict:
        started = perf_counter()
        action, source = parse(text, ACTIONS)
        parse_ms = (perf_counter() - started) * 1000

        key = f"{action.verb}|{action.part}"
        spec = ACTIONS.get(key)

        arms, timings = [], []
        for index, (name, tagline, decide) in enumerate(ARMS):
            at = perf_counter()
            decision = decide(
                action=action, twin=self.twin, actions=ACTIONS, steps=STEPS, tree=TREE
            )
            timings.append(round((perf_counter() - at) * 1000, 2))

            moves = (
                decision.status is Status.ADMIT
                and bool(spec)
                and spec.get("mutates", True)
            )
            arms.append(
                {
                    "name": name,
                    "tagline": tagline,
                    "status": decision.status.value,
                    "code": decision.code,
                    "message": decision.message,
                    "moves": moves,
                    "focus": action.part,
                    "blocker": decision.blocker,
                    "note": self._note(decision, moves),
                    "trace": self._trace(index, action),
                    "after": self._after(spec) if moves else sorted(self.twin.state),
                }
            )

        if arms[-1]["moves"]:
            self.twin.apply(action, spec)

        return {
            "parse": {
                "verb": action.verb,
                "part": action.part,
                "source": source,
                "text": text,
            },
            "arms": arms,
            "twin": self.state(),
            "timings": {"parse_ms": round(parse_ms, 1), "arms": timings},
        }

    def _trace(self, index: int, action: Action) -> list[dict]:
        """What each component of this arm produced, so the page can show the pipeline."""
        spec = ACTIONS.get(f"{action.verb}|{action.part}")
        rows = [
            {"stage": "parse", "value": f"{action.verb} · {action.part or 'no part'}"}
        ]

        if index == 0:
            state = "pass" if spec else "fail"
            rows.append(
                {
                    "stage": "execute",
                    "value": "no check" if spec else "no such action",
                    "state": state,
                }
            )
            return rows

        found = manual_check.best_step(action, STEPS) if action.part else None
        if index == 2:
            path = trail(action.part, TREE) if action.part else []
            ok, why = (
                reachable(action.part, TREE, self.twin.state)
                if action.part
                else (False, "no part")
            )
            rows.append(
                {
                    "stage": "hierarchy",
                    "value": " › ".join(path) or "not on the twin",
                    "state": "pass" if ok else "fail",
                }
            )
            if not ok:
                rows.append({"stage": "stopped", "value": why, "state": "fail"})
                return rows

        rows.append(
            {
                "stage": "manual",
                "value": f"step {found}" if found else "no instruction",
                "state": "pass" if found else "fail",
            }
        )
        if found and found != self.twin.step:
            rows.append(
                {
                    "stage": "stopped",
                    "value": f"manual is at step {self.twin.step}",
                    "state": "fail",
                }
            )
            return rows

        if index == 2 and spec:
            missing = [
                flag for flag in spec.get("requires", []) if flag not in self.twin.state
            ]
            rows.append(
                {
                    "stage": "state",
                    "value": "needs " + " and ".join(missing)
                    if missing
                    else "preconditions hold",
                    "state": "fail" if missing else "pass",
                }
            )
        return rows

    def _after(self, spec: dict) -> list[str]:
        """The state this action would leave behind, without touching the real twin."""
        state = set(self.twin.state)
        if spec.get("sets"):
            state.add(spec["sets"])
        state.difference_update(spec.get("clears", []))
        return sorted(state)

    @staticmethod
    def _note(decision: Decision, moves: bool) -> str:
        if moves:
            return "the action runs on the twin"
        if decision.status is Status.ADMIT:
            return "read-only: the twin does not change"
        if decision.blocker:
            return f"{label(decision.blocker)} is in the way"
        if decision.code in {"OUT_OF_SEQUENCE", "NOT_IN_MANUAL"}:
            return "the part is marked; nothing moves"
        if decision.code == "UNKNOWN_PART":
            return "there is no such part on the twin"
        if decision.code == "AMBIGUOUS_REFERENCE":
            return "nothing to point at"
        return "nothing moves"

    @staticmethod
    def _command(step: int) -> str:
        for spec in ACTIONS.values():
            if step in spec.get("procedure_steps", []):
                return spec["label"]
        return ""

    def state(self) -> dict:
        return {
            "step": self.twin.step,
            "total": len(STEPS),
            "state": sorted(self.twin.state),
            "steps": [
                {
                    "n": n,
                    "text": text,
                    "command": self._command(n),
                    "done": n < self.twin.step,
                    "current": n == self.twin.step,
                }
                for n, text in STEPS.items()
            ],
        }


class Command(BaseModel):
    text: str


app = FastAPI(title="voice-to-twin-gate")
session = Session()


@app.post("/api/command")
def command(body: Command) -> dict:
    return session.run(body.text.strip())


@app.get("/api/state")
def state() -> dict:
    return session.state()


@app.post("/api/reset")
def reset() -> dict:
    session.reset()
    return session.state()


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
