import re
from pathlib import Path

import yaml

POLICY_DIR = Path(__file__).resolve().parent.parent / "policy"


def load_actions(path: Path = POLICY_DIR / "actions.yaml") -> dict[str, dict]:
    """Keyed by "verb|part" so a lookup cannot succeed on half a command."""
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {f"{row['verb']}|{row['part']}": row for row in rows}


def load_manual(path: Path = POLICY_DIR / "manual.md") -> dict[int, str]:
    """The numbered steps of the procedure, as the 2023 arm reads them."""
    steps = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        found = re.match(r"^(\d+)\.\s+(.+)$", line.strip())
        if found:
            steps[int(found.group(1))] = found.group(2)
    return steps
