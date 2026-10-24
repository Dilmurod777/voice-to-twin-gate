# voice-to-twin-gate

Speech becomes a checked action on a 3D aircraft. The gate has two outcomes: the action
runs, or it is refused with a reason. The refusal is the point.

**Live:** https://voice-to-twin-gate.vercel.app — the free instance has no model, so it
parses with the keyword table and says so.

## Watch it

https://github.com/user-attachments/assets/ed1d1976-51ea-467c-bc68-df2aee8b6566

59 seconds, no narration. Every step carries a note that says what just happened and why,
and the aircraft in each column is the same one. The file is also in the repo:
[`docs/demo.mp4`](docs/demo.mp4).

The clip is transcribed and parsed, the panel opens
at step 1, then the valve - which the manual lists as step 3 - is **admitted** by the LLM
arm and **refused** by both checking arms, for two different reasons. It ends on the
measurement below.

## The 20 seconds

| You say | Gate says | Screen |
|---|---|---|
| "remove the access panel" | **ADMIT** — panel 12A, step 1 | panel swings open |
| "open the fuel valve" | **REFUSE** — fuel system is not depressurised | nothing moves |
| "remove the hydraulic pump" | **REFUSE** — procedure is at step 2; pump is step 6 | nothing moves |
| "show the landing gear" | **ADMIT** — read-only | gear highlights |

## The measurement

Same recorded parse, three validators, 24 commands (`python -m eval.run_eval`):

| arm | unsafe executed | legitimate admitted | malformed refused |
|---|---|---|---|
| LLM only | 13/13 | 6/6 | 0/5 |
| Manual check (2023) | 6/13 | 4/6 | 4/5 |
| Context gate (2026) | **0/13** | **6/6** | **5/5** |

The 2023 arm is not weak — it stops the wrong step and most malformed commands. It
fails where the manual cannot help: it executes a valve that is still pressurised, and
a filter behind a closed panel. It also refuses a legitimate "show me the landing gear",
because a view is not an instruction. The 2026 arm is the only one that is both safe and
not obstructive.

The parse is an input, not an experiment: the same recorded LLM output feeds every arm,
so the columns differ only in validation.

## The page

One command, one page, three answers — each animated on the same aircraft from the same camera,
so the eye compares rather than explores.

- **A live parse.** The parser is a local model (Ollama) with a keyword fallback when it is not
  running. The strip above the arms says which one answered and how long it took: about 3 s for
  the model, 0.1 ms for the fallback, and 0.1 ms for all three validators together. The expensive
  part of this system is the language, not the safety check.
- **Three verdicts.** ADMIT or REFUSE, the reason code, and one sentence a technician could act on.
- **Three twins.** The airframe is schematic: a NASA hull is one mesh with no part hierarchy, so
  the service points — hatch, valve, filter, pump, gear — are primitives pinned to it. Each arm
  reports the state it *would* have left behind, so its view animates that hypothetical. On a
  refusal the 2026 view marks what is actually in the way: the closed hatch, not the valve behind it.
- **Loading is shown, not faked.** The form locks, the pipeline strip sweeps, and the bays say what
  they are waiting for.

Three.js is vendored in `public/vendor/` so the demo runs with no network.

## Quickstart

```bash
uv venv
uv pip install -e ".[dev]"
.\.venv\Scripts\python -m pytest          # 44 tests, no model needed
.\.venv\Scripts\python -m uvicorn app.main:app --port 8017
```

Open http://127.0.0.1:8017 and type a command, or press ▶ on a clip. The parse line above
the verdicts says `model` when Ollama answered and `keyword` when it did not — the page
says which, because a lookup table presented as a model would be a lie. Speech-to-text
needs `uv pip install -e ".[asr]"`; without it the page falls back to each clip's own
transcript and labels the run `clip (baked)`.

## Deploy

One container, no models. `VTG_NO_ASR=1` turns speech-to-text off, and with no Ollama on
the host the parse falls back to the keyword parser. The page says which one ran:
`parse: keyword` in the flow strip and `clip (baked)` in the heard line, because each clip
was generated from its own text.

```bash
docker build -t vtg-demo .
docker run -p 8000:8000 vtg-demo
```

On Render: New → Web Service → this repository → Runtime **Docker**, free instance. The
process binds `$PORT`, which Render sets. Nothing else to configure.

On Vercel (free Hobby, no card): import the repository and keep the detected **FastAPI**
preset. `public/` is served from the CDN, `app/main.py` becomes the function, and the
aircraft snapshot rides in a cookie because each request may land on a different
instance. Set `VTG_NO_ASR=1` — the free plan has no speech model, so the clips fall back
to their own transcripts.

## Datasets

| What | Source | Licence | Used for |
|---|---|---|---|
| Airframe | NASA Airborne Science 3D models, e.g. `G3_LARC_GND_0824.glb` | NASA-produced, not copyrighted | the schematic airframe follows its proportions; the GLB itself is not shipped |
| Procedures | FAA-H-8083-30B/31B/32B, *Aviation Maintenance Technician Handbook* | US Government work, public domain | step order and preconditions, cited per step |
| Commands | 14 clips synthesised locally with Windows SAPI | CC BY 4.0 | the demo's speech input |

The NASA GLB is a single mesh with eight materials and no part hierarchy, so the twin in the
browser is a schematic airframe plus seven fabricated parts (panel, valve, filter, pump,
gear, cowl) placed at named anchors. Part IDs are ours.

There is no public aircraft-maintenance speech corpus — ATCO2 and UWB-ATCC are air-traffic
radio, not maintenance, and both are licence-gated — so the demo speaks through synthesised
clips. A real evaluation would need recorded speech; the ASR path accepts it unchanged.

## Layout

```
app/            gate, twin state, policy loading, API
app/approaches/ llm_only (baseline), manual_check (2023), context_gate (2026)
policy/         actions, manual.md, hierarchy.json — readable rules, no PDF parsing
public/         the page, the 3D twin, the clip audio
eval/           command set and the three-arm runner
tests/
docs/           the demo video
```

## Licence

Code MIT. Audio CC BY 4.0. Models and manuals keep their own terms, credited above.

