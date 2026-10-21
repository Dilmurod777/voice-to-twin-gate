# voice-to-twin-gate

Speech becomes a checked action on a 3D aircraft. The gate has two outcomes: the action
runs, or it is refused with a reason. The refusal is the point.

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

## Quickstart

```bash
pip install -e ".[dev]"
powershell -File scripts/fetch_assets.ps1   # NASA airframe + FAA handbook chapters
pytest
```

The gate and policy are in place and tested (`pytest` — 15 passing). The demo itself is
not built yet; `docs/plan.md` is the build order.

## Datasets

| What | Source | Licence | Used for |
|---|---|---|---|
| Airframe, GLB | NASA Airborne Science 3D models, e.g. `G3_LARC_GND_0824.glb` | NASA-produced, not copyrighted | the twin's geometry |
| Procedures | FAA-H-8083-30B/31B/32B, *Aviation Maintenance Technician Handbook* | US Government work, public domain | step order and preconditions, cited per step |
| Commands | recorded here: 40 utterances, two speakers | CC BY 4.0 | ASR error and the unsafe-action A/B |

The NASA GLB is a single mesh with eight materials and no part hierarchy, so the twin is
the airframe plus seven fabricated parts (panel, valve, filter, pump, gear, cowl) placed
at named anchors. Part IDs are ours; the airframe is NASA's.

There is no public aircraft-maintenance speech corpus. ATCO2 and UWB-ATCC are air-traffic
radio, not maintenance, and both are licence-gated. Recording is the honest option, and
forty clips is an afternoon.

## Layout

```
app/            gate, twin state, policy loading, API
app/approaches/ llm_only (baseline), manual_check (2023), context_gate (2026)
policy/         actions, manual.md, hierarchy.json — readable rules, no PDF parsing
web/            Three.js page
eval/           command set and the three-arm runner
tests/
docs/           plan and decisions
```

## Licence

Code MIT. Audio CC BY 4.0. Models and manuals keep their own terms, credited above.
