"""The scene protocol: the brain streams JSON Lines, one op per line.

Each op is a JSON object with an "op" field naming a primitive, e.g.
    {"op":"card","title":"How a jet hovers"}
    {"op":"pin","x":640,"y":310,"text":"1 · Fan"}

OpStreamParser turns arbitrary text deltas into complete ops as soon as each
line finishes, so the overlay draws while the model is still talking.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

Op = dict[str, Any]


@dataclass
class OpStreamParser:
    """Incremental JSONL parser that tolerates the ways LLMs break JSONL.

    - Code fences and blank lines are skipped.
    - A line of plain prose becomes {"op":"say","text":...} instead of being lost.
    - A JSON object without "op" is dropped.
    """

    _buf: str = field(default="", repr=False)

    def feed(self, delta: str) -> list[Op]:
        self._buf += delta
        *lines, self._buf = self._buf.split("\n")
        return [op for line in lines if (op := parse_line(line)) is not None]

    def flush(self) -> list[Op]:
        line, self._buf = self._buf, ""
        op = parse_line(line)
        return [op] if op is not None else []


def parse_line(line: str) -> Op | None:
    line = line.strip()
    if not line or line.startswith("```"):
        return None
    if line.startswith("{"):
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            return None
        if isinstance(obj, dict) and isinstance(obj.get("op"), str):
            return obj
        return None
    return {"op": "say", "text": line}
