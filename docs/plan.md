# voice-to-twin-gate — implementation plan

**Goal:** a public demo where a spoken maintenance command is admitted or refused by a
deterministic gate, with the refusal visible on a 3D aircraft.

**Architecture:** the language model only *proposes* an action (`verb`, `part`). A pure
validator checks it against policy (preconditions, procedure step, read-only) and returns
one of two outcomes. The twin state changes only on ADMIT.

**Stack:** FastAPI, Pydantic, faster-whisper, one local LLM (Ollama or any
OpenAI-compatible endpoint), Three.js, pytest.

**Constraints:** no NDA data; two outcomes only; every README claim is a measured number;
`pip install -e ".[dev]"` then `pytest` must work on a clean machine.

## Review focus

- An action whose text is valid but whose **part is missing** ("remove it") must not be
  guessed — it is refused as ambiguous.
- A read-only inspection must be admitted even mid-procedure, and must not mutate state.
- A refusal must never advance the procedure step.
- The public page and the local mic run the **same** gate and policy; only the input differs.

## Tasks

### 1. Gate and policy — done
`app/gate.py`, `app/policy.py`, `policy/*.yaml`, `tests/test_gate.py` (15 tests, green).
Seven actions, six-step procedure, three refusal reasons.

### 2. Twin scene
Load the NASA GLB in Three.js; add seven interactive parts at named anchors in Blender
(panel, valve, filter, pump, gear, cowl, drain) and export one GLB per movable part.
Done when clicking `#access_panel` opens the panel and `#landing_gear` highlights it.

### 3. API
`app/main.py`: `POST /command {text}` → parse → gate → apply effect → return decision and
state. `GET /state`. State is a dict in memory; one session, no auth.
Tests: refused command leaves state byte-identical; admitted `open_panel` flips
`panel_open` and advances to step 2.

### 4. Language model
`app/llm.py`: one call, JSON schema constrained, returns `{verb, part}` from a closed
vocabulary; unknown verb or part is passed through to the gate rather than repaired.
Default endpoint Ollama on `127.0.0.1:11434`, overridable by `OPENAI_BASE_URL`.
Tests: a model reply with an unknown part becomes `UNKNOWN_PART`, not an exception.

### 5. Speech
`app/asr.py`: faster-whisper `small.en`, VAD, 16 kHz. Browser mic → 10 s wav → transcript.
Metric recorded: word error rate on 40 clips, two speakers.

### 6. Eval and the number
`eval/run_eval.py`: run `eval/commands.csv` twice — direct execution of the model's
proposal, and through the gate. Print a table: unsafe actions executed per arm.
Done when the table is in the README and the failure cases are listed.

### 7. Deploy and README
Pages + GIF from the local run. Deploy target decided later (typed commands on the public
URL, mic local only) — the gate is identical either way.

## Open decisions

- Public demo input: typed commands, or recorded clips replayed through the same gate.
  Live mic on a public URL needs hosted ASR and a bill.
- The NASA airframe is a single mesh, so part geometry is fabricated. If that reads as
  fake, swap in a CC-BY engine assembly with real parts.
