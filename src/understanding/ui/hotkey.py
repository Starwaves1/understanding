"""Modifier-tap hotkey: press a modifier chord (default ⌃⌥) and release it
without pressing any other key. Chords used with a key (⌃⌥K) don't fire.

The tap logic is a pure state machine (ModifierTap) so it's testable; a
Quartz event tap feeds it.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

from AppKit import (
    NSEventModifierFlagCommand,
    NSEventModifierFlagControl,
    NSEventModifierFlagOption,
    NSEventModifierFlagShift,
)

FLAGS = {
    "control": NSEventModifierFlagControl,
    "option": NSEventModifierFlagOption,
    "command": NSEventModifierFlagCommand,
    "shift": NSEventModifierFlagShift,
}
ESCAPE_KEYCODE = 53
log = logging.getLogger(__name__)


class ModifierTap:
    def __init__(self, target: set[str], max_seconds: float, now: Callable[[], float] = time.monotonic) -> None:
        unknown = target - FLAGS.keys()
        if unknown:
            raise ValueError(f"unknown modifiers {unknown}; use {sorted(FLAGS)}")
        self.target = frozenset(target)
        self.max_seconds = max_seconds
        self.now = now
        self.armed_at: float | None = None

    def modifiers(self, held: set[str]) -> bool:
        """Feed the currently-held modifiers. Returns True when the tap completes."""
        # Software on real Macs (dictation and remapping tools) emits phantom Shift
        # flag changes; unless Shift is part of the chord, it must not cancel a tap.
        held = held - ({"shift"} - self.target)
        if held == self.target:
            if self.armed_at is None:
                self.armed_at = self.now()
            return False
        if held and held < self.target and self.armed_at is not None:
            return False  # releasing the chord one key at a time
        if not held and self.armed_at is not None:
            fired = self.now() - self.armed_at <= self.max_seconds
            self.armed_at = None
            return fired
        self.armed_at = None
        return False

    def key(self) -> None:
        self.armed_at = None


class Hotkey:
    """Feeds ModifierTap from a listen-only Quartz event tap.

    An NSEvent global monitor stopped receiving keyDown events once our
    non-activating prompt panel had been key (observed 2026-11-03, macOS 27:
    Esc never arrived for 11+ s after a question). A session-level event tap
    sees every key event regardless of which app or window receives it.
    """

    def __init__(
        self,
        modifiers: list[str],
        max_seconds: float,
        on_tap: Callable[[], None],
        on_escape: Callable[[], None],
        on_click: Callable[[], None] | None = None,
    ) -> None:
        import Quartz as Q

        self.tap = ModifierTap(set(modifiers), max_seconds)
        self.on_tap = on_tap
        self.on_escape = on_escape
        self.on_click = on_click
        self._Q = Q
        self._flag_bits = {
            "control": Q.kCGEventFlagMaskControl,
            "option": Q.kCGEventFlagMaskAlternate,
            "command": Q.kCGEventFlagMaskCommand,
            "shift": Q.kCGEventFlagMaskShift,
        }
        mask = (
            Q.CGEventMaskBit(Q.kCGEventKeyDown)
            | Q.CGEventMaskBit(Q.kCGEventFlagsChanged)
            | Q.CGEventMaskBit(Q.kCGEventLeftMouseDown)
        )
        self._port = Q.CGEventTapCreate(
            Q.kCGSessionEventTap, Q.kCGHeadInsertEventTap, Q.kCGEventTapOptionListenOnly, mask, self._callback, None
        )
        if self._port is None:
            raise RuntimeError(
                "could not create the keyboard event tap: grant Accessibility (and Input Monitoring) "
                "to the app that launched this, then restart"
            )
        source = Q.CFMachPortCreateRunLoopSource(None, self._port, 0)
        Q.CFRunLoopAddSource(Q.CFRunLoopGetMain(), source, Q.kCFRunLoopCommonModes)
        Q.CGEventTapEnable(self._port, True)

    def _callback(self, _proxy, etype, event, _refcon):
        # Exceptions here would vanish inside the run loop; log them.
        try:
            self._dispatch(etype, event)
        except Exception:
            log.exception("hotkey handler failed")
        return event

    def _dispatch(self, etype, event) -> None:
        Q = self._Q
        if etype in (Q.kCGEventTapDisabledByTimeout, Q.kCGEventTapDisabledByUserInput):
            log.warning("event tap was disabled (%s); re-enabling", etype)
            Q.CGEventTapEnable(self._port, True)
            return
        if etype == Q.kCGEventLeftMouseDown:
            if self.on_click:
                self.on_click()
            return
        if etype == Q.kCGEventKeyDown:
            code = Q.CGEventGetIntegerValueField(event, Q.kCGKeyboardEventKeycode)
            self.tap.key()
            if code == ESCAPE_KEYCODE:
                self.on_escape()
            return
        flags = Q.CGEventGetFlags(event)
        held = {name for name, bit in self._flag_bits.items() if flags & bit}
        log.debug("flags %s armed=%s", sorted(held), self.tap.armed_at)
        if self.tap.modifiers(held):
            self.on_tap()
