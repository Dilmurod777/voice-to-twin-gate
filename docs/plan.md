# voice-to-twin-gate — implementation plan

**Goal:** a public demo where the same spoken command is run through three validators —
the language model alone, the 2023 manual checker, and the 2026 context gate — and the
difference is visible on a 3D aircraft.

**Architecture:** the language model only *proposes* an action (`verb`, `part`). Each arm
decides independently; only an admit applies a mutating effect to the twin.

**Stack:** FastAPI, Pydantic, faster-whisper, one local LLM (Ollama or any
OpenAI-compatible endpoint), Three.js, pytest.

**Constraints:** no NDA data; two outcomes per arm; every README claim is a measured
number; `pip install -e ".[dev]"` then `pytest` must work on a clean machine.

## Review focus

- An action whose text is valid but whose **part is missing** ("remove it") must not be
  guessed — it is refused as ambiguous.
- A read-only inspection must be admitted even mid-procedure by the 2026 arm, and must not
  mutate state.
- A refusal must never advance the procedure step.
- The public page and the local mic run the **same** gate and policy; only the input differs.

## Tasks

### 1. Three arms, policy, hierarchy — done
`app/approaches/{llm_only,manual_check,context_gate}.py`, `app/gate.py`, `app/twin.py`,
`policy/{actions.yaml,manual.md,hierarchy.json}`, `eval/run_eval.py`.
31 tests green; the README table is produced by `python -m eval.run_eval`.
Open: grow `eval/commands.csv` from 24 to 40.

### 2. Twin scene
Load the NASA GLB in Three.js; add schematic service points (panel plate, valve wheel,
filter canister, pump, gear leg) as primitives at named anchors — the airframe has no part
hierarchy, so these are overlays, not modelled systems. Done when clicking `#access_panel`
opens the plate and `#landing_gear` highlights it.

### 3. API
`app/main.py`: `POST /command {text, arm}` → parse → decide → apply → return decision and
state. `GET /state`. One in-memory session, no auth.
Tests: a refused command leaves state byte-identical; an admitted `open_panel` sets
`access_panel_open` and advances to step 2.

### 4. Language model
`app/llm.py`: one call, JSON-schema constrained, returns `{verb, part}` from a closed
vocabulary taken from `actions.yaml`. Unknown values pass through to the arms rather than
being repaired.
Tests: a reply with an unknown part reaches the gate as `UNKNOWN_PART`, not an exception.

### 5. Speech
`app/asr.py`: faster-whisper `small.en`, VAD, 16 kHz. Browser mic → wav → transcript.
Metric recorded: word error rate on 40 clips, two speakers.

### 6. Eval at full size
Forty commands, the same three-arm table, plus per-command reason codes so a reviewer can
see which layer refused what.

### 7. Deploy and README
Pages plus a GIF from the local run. Deploy target still open: typed commands on the public
URL with the mic local, or recorded clips replayed through the same three arms.

## Open decisions

- Public demo input: typed commands or recorded clips. Live mic on a public URL needs
  hosted ASR and a bill.
- The NASA airframe is a single mesh, so service points are overlays. If that reads as
  fake, swap in a CC-BY engine assembly with real part separation.
