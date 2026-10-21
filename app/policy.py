from pathlib import Path

import yaml

POLICY_DIR = Path(__file__).resolve().parent.parent / "policy"


def load_actions(path: Path = POLICY_DIR / "actions.yaml") -> dict[str, dict]:
    """Keyed by "verb|part" so a lookup cannot succeed on half a command."""
    rows = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {f"{row['verb']}|{row['part']}": row for row in rows}


def load_procedure(path: Path = POLICY_DIR / "procedure.yaml") -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))
