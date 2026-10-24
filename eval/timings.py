"""p50/p95 for the two halves of a command: the model parse and the gate.

The eval fixes the parse so the three arms differ only in validation; this does the
opposite and measures the pipeline a user waits on. Needs a model at OLLAMA_URL:

    python -m eval.timings

Every command must come back from the model, not the keyword fallback, or the parse
numbers are a lookup table's and the run is refused.
"""

import csv
from math import ceil
from pathlib import Path
from time import perf_counter

from app.approaches import context_gate
from app.llm import MODEL, parse
from app.policy import load_actions, load_manual
from app.twin import Twin, load_hierarchy

ROWS = Path(__file__).resolve().parent / "commands.csv"


def pct(values: list[float], p: float) -> float:
    """Nearest-rank percentile: no interpolation to explain."""
    ordered = sorted(values)
    return ordered[max(ceil(p / 100 * len(ordered)) - 1, 0)]


def main() -> None:
    rows = list(csv.DictReader(ROWS.open(encoding="utf-8")))
    actions, steps, tree = load_actions(), load_manual(), load_hierarchy()
    parses, gates, sources = [], [], {}

    for row in rows:
        started = perf_counter()
        action, source = parse(row["text"], actions)
        parses.append((perf_counter() - started) * 1000)
        sources[source] = sources.get(source, 0) + 1

        twin = Twin(
            step=int(row["step"]), state=set(filter(None, row["state"].split(";")))
        )
        started = perf_counter()
        context_gate.decide(
            action=action, twin=twin, actions=actions, steps=steps, tree=tree
        )
        gates.append((perf_counter() - started) * 1000)

    print(f"{len(rows)} commands · {MODEL} · parse by {sources}")
    if sources != {"model": len(rows)}:
        raise SystemExit(
            "a command fell back to the keyword parser; numbers not logged"
        )

    print(f"{'':6} {'p50':>10} {'p95':>10}")
    for name, values in (("parse", parses), ("gate", gates)):
        print(f"{name:6} {pct(values, 50):>8.2f}ms {pct(values, 95):>8.2f}ms")


if __name__ == "__main__":
    main()
