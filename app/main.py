"""The demo server: one in-memory aircraft, three validators per command.

A command is answered in two calls so the three approaches can finish independently:
`POST /api/command` parses once and freezes the aircraft state, then each
`POST /api/arm/{i}` decides its own arm against that same snapshot and returns on its own.
Only arm 2 — the gate — ever changes the real twin.
"""

from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException
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
        self.pending: dict | None = None

    def prepare(self, text: str) -> dict:
        """Parse once and freeze the state the three arms will argue about."""
        started = perf_counter()
        action, source = parse(text, ACTIONS)
        parse_ms = (perf_counter() - started) * 1000

        self.pending = {
            "action": action,
            "source": source,
            "text": text,
            "twin": Twin(step=self.twin.step, state=set(self.twin.state)),
            "applied": False,
        }

        return {
            "parse": {
                "verb": action.verb,
                "part": action.part,
                "source": source,
                "text": text,
            },
            "twin": self.state(),
            "timings": {"parse_ms": round(parse_ms, 1)},
        }

    def arm(self, index: int) -> dict:
        if self.pending is None:
            raise HTTPException(status_code=409, detail="no command in flight")

        pending = self.pending
        action: Action = pending["action"]
        twin: Twin = pending["twin"]  # every arm reads the same frozen state
        spec = ACTIONS.get(f"{action.verb}|{action.part}")

        started = perf_counter()
        decision = ARMS[index][2](
            action=action, twin=twin, actions=ACTIONS, steps=STEPS, tree=TREE
        )
        elapsed = round((perf_counter() - started) * 1000, 2)

        moves = (
            decision.status is Status.ADMIT and bool(spec) and spec.get("mutates", True)
        )
        if index == 2 and moves and not pending["applied"]:
            self.twin.apply(action, spec)
            pending["applied"] = True

        return {
            "arm": {
                "index": index,
                "name": ARMS[index][0],
                "tagline": ARMS[index][1],
                "status": decision.status.value,
                "code": decision.code,
                "message": decision.message,
                "moves": moves,
                "focus": action.part,
                "blocker": decision.blocker,
                "note": self._note(decision, moves),
                "after": self._after(spec, twin) if moves else sorted(twin.state),
                "ms": elapsed,
                "trace": self._trace(index, action, twin),
            },
            "twin": self.state(),
        }

    def _trace(self, index: int, action: Action, twin: Twin) -> list[dict]:
        """The stages this arm actually ran, with the value each one produced."""
        if not action.part:
            return [
                {"stage": "parse", "value": f"{action.verb} · no part", "state": "fail"}
            ]

        spec = ACTIONS.get(f"{action.verb}|{action.part}")
        rows = [{"stage": "parse", "value": f"{action.verb} · {action.part}"}]

        if index == 0:
            rows.append(
                {
                    "stage": "execute",
                    "value": f"{action.verb}({action.part})"
                    if spec
                    else "no such action",
                    "state": "pass" if spec else "fail",
                }
            )
            return rows

        found = manual_check.best_step(action, STEPS)

        if index == 2:
            path = trail(action.part, TREE)
            ok, why = reachable(action.part, TREE, twin.state)
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
        if found and found != twin.step:
            rows.append(
                {
                    "stage": "stopped",
                    "value": f"manual is at step {twin.step}",
                    "state": "fail",
                }
            )
            return rows

        if index == 2 and spec:
            missing = [
                flag for flag in spec.get("requires", []) if flag not in twin.state
            ]
            rows.append(
                {
                    "stage": "state",
                    "value": ("needs " + " and ".join(missing))
                    if missing
                    else "preconditions hold",
                    "state": "fail" if missing else "pass",
                }
            )
        return rows

    @staticmethod
    def _after(spec: dict, twin: Twin) -> list[str]:
        """The state this action would leave behind, without touching the real twin."""
        state = set(twin.state)
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
                    "done": n < self.twin.step,
                    "current": n == self.twin.step,
                    "command": self._command(n),
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
    return session.prepare(body.text.strip())


@app.post("/api/arm/{index}")
def arm(index: int) -> dict:
    if not 0 <= index < len(ARMS):
        raise HTTPException(status_code=404, detail="no such arm")
    return session.arm(index)


@app.get("/api/state")
def state() -> dict:
    return session.state()


@app.post("/api/reset")
def reset() -> dict:
    session.reset()
    return session.state()


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
