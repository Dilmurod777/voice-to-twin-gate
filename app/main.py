"""The demo server: one in-memory aircraft, three validators per command.

A command is parsed once and the aircraft is frozen into a snapshot; each arm then answers
on its own request against that snapshot, so a slow arm cannot hold up a fast one. Only
the 2026 arm moves the real twin.
"""

from pathlib import Path
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app import asr
from app.approaches import context_gate, llm_only, manual_check
from app.llm import parse
from app.policy import load_actions, load_manual
from app.schema import Action, Decision, Status, Step
from app.twin import Twin, load_hierarchy

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

    def prepare(self, text: str, asr_ms: float = 0) -> dict:
        started = perf_counter()
        action, source = parse(text, ACTIONS)
        parse_ms = round((perf_counter() - started) * 1000, 1)
        self.pending = {
            "action": action,
            "source": source,
            "text": text,
            "twin": Twin(step=self.twin.step, state=set(self.twin.state)),
            "applied": False,
            "parse_ms": parse_ms,
            "asr_ms": asr_ms,
        }
        return {
            "parse": {
                "verb": action.verb,
                "part": action.part,
                "source": source,
                "text": text,
            },
            "twin": self.state(),
            "timings": {"parse_ms": parse_ms, "asr_ms": asr_ms},
        }

    def arm(self, index: int) -> dict:
        if self.pending is None:
            raise HTTPException(status_code=409, detail="no command in flight")

        pending = self.pending
        action: Action = pending["action"]
        started = perf_counter()
        decision: Decision = ARMS[index][2](
            action=action, twin=pending["twin"], actions=ACTIONS, steps=STEPS, tree=TREE
        )
        ms = round((perf_counter() - started) * 1000, 3)

        spec = ACTIONS.get(f"{action.verb}|{action.part}")
        moves = (
            decision.status is Status.ADMIT and bool(spec) and spec.get("mutates", True)
        )

        if index == 2 and moves and not pending["applied"]:
            self.twin.apply(action, spec)
            pending["applied"] = True

        rows = [
            *(
                [Step(stage="whisper", value="small.en · 16 kHz", ms=pending["asr_ms"])]
                if pending.get("asr_ms")
                else []
            ),
            Step(
                stage="parse",
                value=f"{action.verb} · {action.part or 'no part'}",
                ms=pending["parse_ms"],
            ),
            *decision.trace,
        ]
        overhead = max(ms - sum(row.ms for row in rows), 0)
        rows.append(
            Step(
                stage="decision",
                value=f"{decision.status.value} · {decision.code}",
                state="pass" if decision.status is Status.ADMIT else "fail",
                ms=round(overhead, 3),
            )
        )

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
                "after": self._after(spec, pending["twin"])
                if moves
                else sorted(pending["twin"].state),
                "ms": ms,
                "trace": [row.model_dump() for row in rows],
            },
            "twin": self.state(),
        }

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
    asr_ms: float = 0


app = FastAPI(title="voice-to-twin-gate")
session = Session()


@app.post("/api/command")
def command(body: Command) -> dict:
    return session.prepare(body.text.strip(), body.asr_ms)


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


@app.post("/api/transcribe")
async def transcribe(request: Request) -> dict:
    audio = await request.body()
    if len(audio) < 800:
        raise HTTPException(422, "no audio")
    started = perf_counter()
    text = await run_in_threadpool(asr.transcribe, audio)
    return {"text": text, "ms": round((perf_counter() - started) * 1000, 1)}


app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
