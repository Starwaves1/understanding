"""Replays a JSONL file as if a model were streaming it. Exercises the whole
pipeline (hotkey → panel → session → renderer) with no model and no cost."""

from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

from understanding.brains import Turn, register

DEMO = Path(__file__).resolve().parent.parent / "web" / "demo.jsonl"


@register("replay")
class ReplayBrain:
    def __init__(self, path: str | None = None, delay: float = 0.25, **_ignored) -> None:
        self.path = Path(path) if path else DEMO
        self.delay = delay
        self._stop = False

    def start(self) -> None: ...

    def stream(self, turn: Turn) -> Iterator[str]:
        self._stop = False
        for line in self.path.read_text().splitlines(keepends=True):
            if self._stop:
                return
            time.sleep(self.delay)
            yield line

    def interrupt(self) -> None:
        self._stop = True

    def reset(self) -> None: ...

    def close(self) -> None: ...
