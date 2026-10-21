"""The twin: a hierarchy of nodes, a procedure step, and what is currently true.

A part behind a closed panel is not reachable — that is the 3D check, and it is done by
walking the tree rather than by trusting a flag the language model could set.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

HIERARCHY = Path(__file__).resolve().parent.parent / "policy" / "hierarchy.json"


def load_hierarchy(path: Path = HIERARCHY) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _path_to(node_id: str, tree: dict, trail: tuple = ()) -> tuple | None:
    here = trail + (tree,)
    if tree["id"] == node_id:
        return here
    for child in tree.get("children", []):
        found = _path_to(node_id, child, here)
        if found:
            return found
    return None


def reachable(part: str, tree: dict, state: set[str]) -> tuple[bool, str]:
    """(reachable, why not). A door is open when "<id>_open" is in the state."""
    path = _path_to(part, tree)
    if path is None:
        return False, f"'{part}' is not in the twin's hierarchy"
    for node in path[:-1]:
        if node.get("door") and f"{node['id']}_open" not in state:
            return False, f"{node['label']} is closed"
    return True, ""


def blocker(part: str, tree: dict, state: set[str]) -> str | None:
    """The closed door standing between the user and the part, if there is one."""
    path = _path_to(part, tree)
    if path is None:
        return None
    for node in path[:-1]:
        if node.get("door") and f"{node['id']}_open" not in state:
            return node["id"]
    return None


@dataclass
class Twin:
    step: int
    state: set[str] = field(default_factory=set)

    def apply(self, action, spec: dict) -> None:
        """Called only after an ADMIT, and only for actions that mutate."""
        if spec.get("sets"):
            self.state.add(spec["sets"])
        for flag in spec.get("clears", []):
            self.state.discard(flag)
        if self.step in spec.get("procedure_steps", []):
            self.step += 1


def trail(part: str, tree: dict) -> list[str]:
    """Labels from the root down to the part, for showing where a command landed."""
    path = _path_to(part, tree)
    return [node["label"] for node in path] if path else []
