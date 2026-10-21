"""The demo server: one in-memory aircraft, three validators per command.

The gate is the system of record. The other two arms are counterfactuals on the same
state: they answer what would have happened, and the twin only moves when the gate says
so.
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.approaches import context_gate, llm_only, manual_check
from app.llm import parse
from app.policy import load_actions, load_manual
from app.schema import Action, Status
from app.twin import Twin, load_hierarchy

WEB = Path(__file__).resolve().parent.parent / "web"
ACTIONS, STEPS, TREE = load_actions(), load_manual(), load_hierarchy()

ARMS = [
    ("LLM only", "executes the parse", llm_only.decide),
    ("Manual check · 2023", "the manual, and only the manual", manual_check.decide),
    ("Context gate · 2026", "manual + 3D hierarchy + state", context_gate.decide),
]


class Session:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.twin = Twin(step=1)

    def run(self, text: str) -> dict:
        action, source = parse(text, ACTIONS)
        key = f"{action.verb}|{action.part}"
        spec = ACTIONS.get(key)

        arms = []
        for name, tagline, decide in ARMS:
            decision = decide(
                action=action, twin=self.twin, actions=ACTIONS, steps=STEPS, tree=TREE
            )
            arms.append(
                {
                    "name": name,
                    "tagline": tagline,
                    "status": decision.status.value,
                    "code": decision.code,
                    "message": decision.message,
                    "moves": decision.status is Status.ADMIT
                    and bool(spec)
                    and spec.get("mutates", True),
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
        }

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
