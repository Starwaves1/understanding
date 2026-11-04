"""The orchestrator: context → brain → op parser → renderer.

UI-agnostic. The macOS overlay, the headless CLI, and tests all plug in as a
Renderer. Turns run one at a time on a worker thread; asking a new question
interrupts the current answer.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Protocol

from understanding import context
from understanding.brains import Brain, Turn
from understanding.protocol import Op, OpStreamParser

log = logging.getLogger(__name__)


class Renderer(Protocol):
    def begin(self, question: str, frame: tuple[int, int] | None, anchors: list[dict]) -> None: ...
    def apply(self, op: Op) -> None: ...
    def end(self, error: str | None) -> None: ...


@dataclass
class _Job:
    question: str
    snapshot: Future[context.Contribution] | None
    cancelled: threading.Event


class Session:
    def __init__(self, brain: Brain, providers: list[context.Provider], renderer: Renderer) -> None:
        self.brain = brain
        self.providers = providers
        self.renderer = renderer
        self._pending_snapshot: Future[context.Contribution] | None = None
        self._jobs: queue.Queue[_Job | None] = queue.Queue()
        self._current: _Job | None = None
        self._worker = threading.Thread(target=self._run, name="session", daemon=True)

    def start(self) -> None:
        self._worker.start()
        self._jobs.put(None)  # warm the brain on the worker thread

    def prepare(self) -> None:
        """Hotkey fired: snapshot the screen now, before our prompt box appears."""
        self._pending_snapshot = context.snapshot(self.providers) if self.providers else None

    def submit(self, question: str) -> None:
        question = question.strip()
        if not question:
            return
        snap, self._pending_snapshot = self._pending_snapshot, None
        if self._current:
            self._current.cancelled.set()
            self.brain.interrupt()
        self._jobs.put(_Job(question, snap or (context.snapshot(self.providers) if self.providers else None), threading.Event()))

    def cancel(self) -> None:
        if self._current:
            self._current.cancelled.set()
            self.brain.interrupt()

    def reset(self) -> None:
        self.cancel()
        self._jobs.put(_Job("/new", None, threading.Event()))

    # -- worker ----------------------------------------------------------------
    def _run(self) -> None:
        while True:
            job = self._jobs.get()
            if job is None:
                self._safe(self.brain.start)
                continue
            if job.question == "/new":
                self._safe(self.brain.reset)
                continue
            self._current = job
            try:
                self._answer(job)
            finally:
                self._current = None

    def _safe(self, fn) -> None:
        try:
            fn()
        except Exception:
            log.exception("brain lifecycle call failed")

    def _answer(self, job: _Job) -> None:
        t0 = time.monotonic()
        snap = job.snapshot.result() if job.snapshot else context.Contribution()
        log.info("context ready after %.2fs (%d images)", time.monotonic() - t0, len(snap.images))
        frame = (snap.images[0].width, snap.images[0].height) if snap.images else None
        self.renderer.begin(job.question, frame, snap.anchors)
        turn = Turn(job.question, snap.images, snap.notes)
        parser = OpStreamParser()
        first = None
        error = None
        try:
            for delta in self.brain.stream(turn):
                if job.cancelled.is_set():
                    continue  # drain so the brain's stream stays aligned
                for op in parser.feed(delta):
                    if first is None:
                        first = time.monotonic() - t0
                        log.info("first op after %.2fs: %s", first, op.get("op"))
                    self.renderer.apply(op)
            if not job.cancelled.is_set():
                for op in parser.flush():
                    self.renderer.apply(op)
        except Exception as e:
            log.exception("turn failed")
            error = str(e)
        if not job.cancelled.is_set():
            self.renderer.end(error)
        log.info("turn %r took %.2fs", job.question[:60], time.monotonic() - t0)
