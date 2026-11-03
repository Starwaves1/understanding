"""Brain backed by one long-lived headless Claude Code process.

`claude -p --input-format stream-json` keeps reading user messages from stdin,
so a single warm process serves the whole conversation: no per-question
startup, and follow-ups share context. Measured on Haiku: ~0.5-0.8 s to first
token. The session is persisted, so `claude --resume <id>` picks it up in a
normal terminal.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import queue
import shutil
import subprocess
import threading
import uuid
from collections.abc import Iterator
from pathlib import Path

from understanding.brains import Turn, register

log = logging.getLogger(__name__)
WORKSPACE = Path.home() / ".local" / "share" / "understanding" / "workspace"
_EOF = object()


class BrainError(RuntimeError):
    pass


@register("claude_code")
class ClaudeCodeBrain:
    def __init__(
        self,
        system_prompt: str,
        model: str = "haiku",
        tools: list[str] | None = None,
        extra_args: list[str] | None = None,
        claude_bin: str | None = None,
        cwd: str | None = None,
        effort: str | None = "low",
        thinking: bool = False,
        warmup: bool = True,
    ) -> None:
        self.system_prompt = system_prompt
        self.model = model
        self.tools = tools or []
        self.extra_args = extra_args or []
        self.claude_bin = claude_bin or shutil.which("claude") or "claude"
        self.cwd = Path(cwd).expanduser() if cwd else WORKSPACE
        self.effort = effort
        self.thinking = thinking
        self.warmup = warmup
        self.session_id: str | None = None
        self._proc: subprocess.Popen[str] | None = None
        self._events: queue.Queue = queue.Queue()
        self._write_lock = threading.Lock()
        self._resume_id: str | None = None

    # -- lifecycle -------------------------------------------------------
    def _argv(self) -> list[str]:
        argv = [
            self.claude_bin, "-p",
            "--input-format", "stream-json",
            "--output-format", "stream-json",
            "--verbose",
            "--include-partial-messages",
            "--model", self.model,
            "--system-prompt", self.system_prompt,
            "--tools", ",".join(self.tools),
            # No user/project settings, CLAUDE.md, hooks or MCP: they add startup
            # latency and inject context that fights the drawing protocol.
            "--setting-sources", "",
            "--strict-mcp-config",
        ]
        if self.tools:
            argv += ["--allowedTools", ",".join(self.tools)]
        if self.effort:
            argv += ["--effort", self.effort]
        if self._resume_id:
            argv += ["--resume", self._resume_id]
        else:
            self.session_id = str(uuid.uuid4())
            argv += ["--session-id", self.session_id]
        return argv + self.extra_args

    def start(self) -> None:
        if self._proc and self._proc.poll() is None:
            return
        self.cwd.mkdir(parents=True, exist_ok=True)
        self._events = queue.Queue()
        self._proc = subprocess.Popen(
            self._argv(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            cwd=self.cwd,
            env=self._env(),
        )
        self._resume_id = None
        threading.Thread(target=self._pump, args=(self._proc, self._events), daemon=True).start()
        threading.Thread(target=self._drain_stderr, args=(self._proc,), daemon=True).start()
        log.info("claude started pid=%s model=%s session=%s", self._proc.pid, self.model, self.session_id)
        if self.warmup:
            # The first message in a fresh process pays ~2-3 s of one-time setup;
            # pay it now instead of on the user's first question.
            for _ in self.stream(Turn("(warm-up: reply with an empty line)")):
                pass

    def _env(self) -> dict[str, str]:
        env = dict(os.environ)
        if not self.thinking:
            # Thinking costs 1-7 s before the first visible op; drawing needs speed.
            env["MAX_THINKING_TOKENS"] = "0"
        return env

    @staticmethod
    def _pump(proc: subprocess.Popen[str], events: queue.Queue) -> None:
        assert proc.stdout
        for line in proc.stdout:
            try:
                events.put(json.loads(line))
            except json.JSONDecodeError:
                log.debug("non-json stdout: %s", line.rstrip())
        events.put(_EOF)

    @staticmethod
    def _drain_stderr(proc: subprocess.Popen[str]) -> None:
        assert proc.stderr
        for line in proc.stderr:
            log.warning("claude stderr: %s", line.rstrip())

    def _send(self, obj: dict) -> None:
        if not self._proc or self._proc.poll() is not None:
            raise BrainError("claude process is not running")
        with self._write_lock:
            assert self._proc.stdin
            self._proc.stdin.write(json.dumps(obj) + "\n")
            self._proc.stdin.flush()

    # -- Brain protocol ----------------------------------------------------
    def stream(self, turn: Turn) -> Iterator[str]:
        if not self._proc or self._proc.poll() is not None:
            # Crashed or never started: come back on the same conversation.
            if self.session_id and self._proc is not None:
                self._resume_id = self.session_id
            self.start()
        content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": img.media_type,
                    "data": base64.b64encode(img.data).decode(),
                },
            }
            for img in turn.images
        ]
        notes = list(turn.context_notes)
        for img in turn.images:
            notes.append(f"Screenshot size: {img.width}x{img.height} px.")
        text = ("\n".join(f"[context] {n}" for n in notes) + "\n\n" if notes else "") + turn.question
        content.append({"type": "text", "text": text})
        self._send({"type": "user", "message": {"role": "user", "content": content}})

        while True:
            ev = self._events.get()
            if ev is _EOF:
                raise BrainError("claude exited mid-answer; see log")
            kind = ev.get("type")
            if kind == "stream_event":
                e = ev["event"]
                if e.get("type") == "content_block_delta" and e["delta"].get("type") == "text_delta":
                    yield e["delta"]["text"]
                elif e.get("type") == "message_stop":
                    yield "\n"
            elif kind == "result":
                if ev.get("is_error") and ev.get("subtype") != "error_during_execution":
                    raise BrainError(str(ev.get("result") or ev.get("subtype")))
                log.info(
                    "turn done in %sms cost=$%s",
                    ev.get("duration_ms"),
                    ev.get("total_cost_usd"),
                )
                return

    def interrupt(self) -> None:
        try:
            self._send(
                {
                    "type": "control_request",
                    "request_id": str(uuid.uuid4()),
                    "request": {"subtype": "interrupt"},
                }
            )
        except BrainError:
            pass

    def reset(self) -> None:
        self.close()
        self.start()

    def close(self) -> None:
        if self._proc and self._proc.poll() is None:
            assert self._proc.stdin
            self._proc.stdin.close()
            try:
                self._proc.wait(timeout=2)
            except subprocess.TimeoutExpired:
                self._proc.kill()
        self._proc = None
