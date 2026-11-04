"""Wires config → brain, context, primitives, overlay, panel, hotkey, menu bar."""

from __future__ import annotations

import logging

import objc
from AppKit import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSMenu,
    NSMenuItem,
    NSStatusBar,
    NSVariableStatusItemLength,
)
from Foundation import NSObject
from PyObjCTools import AppHelper

from understanding import brains, context, primitives, prompt
from understanding.config import Config
from understanding.session import Session
from understanding.ui.hotkey import Hotkey
from understanding.ui.overlay import Overlay, OverlayRenderer
from understanding.ui.panel import PromptPanel

log = logging.getLogger(__name__)


def check_accessibility() -> bool:
    from ApplicationServices import AXIsProcessTrustedWithOptions

    trusted = AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
    if not trusted:
        log.warning(
            "Accessibility permission missing: the global hotkey won't fire. Grant it to the app "
            "that launched this (Terminal/iTerm/…) in System Settings ▸ Privacy & Security ▸ Accessibility, then restart."
        )
    return bool(trusted)


class Controller(NSObject):
    def initWithConfig_autoAsk_(self, cfg: Config, auto_ask: str | None):
        self = objc.super(Controller, self).init()
        self.cfg = cfg
        self.auto_ask = auto_ask
        return self

    def applicationDidFinishLaunching_(self, _note) -> None:
        try:
            self._launch()
        except Exception:
            # PyObjC swallows exceptions raised inside delegate callbacks.
            log.exception("startup failed")
            AppHelper.stopEventLoop()

    @objc.python_method
    def _launch(self) -> None:
        cfg = self.cfg
        prims = primitives.select(primitives.discover(), cfg.primitives)
        system_prompt = prompt.compose(prims, cfg.prompt_extra)
        brain = brains.create(cfg.brain, system_prompt=system_prompt, **cfg.brain_options)
        providers = context.build(cfg.context, cfg.context_options)

        self.overlay = Overlay(prims)
        self.session = Session(brain, providers, OverlayRenderer(self.overlay))
        self.overlay.on_close = self.dismiss
        self._hidden_captures = 0
        self.panel = PromptPanel(on_submit=self.submit, on_escape=self.dismiss)
        check_accessibility()  # before the tap, so the permission prompt can appear
        try:
            self.hotkey = Hotkey(
                cfg.hotkey, cfg.tap_max_seconds, on_tap=self.toggle, on_escape=self.escape
            )
        except RuntimeError:
            log.exception("no keyboard event tap: no global hotkey or Esc; use the ◐ menu-bar item to ask, and the card's ✕ to close")
            self.hotkey = None
        self._build_menu()
        self.session.start()
        log.info("ready: tap %s to ask (brain=%s %s)", "+".join(cfg.hotkey), cfg.brain, cfg.brain_options)
        if self.auto_ask:
            AppHelper.callLater(1.5, self._auto)

    @objc.python_method
    def _auto(self) -> None:
        self.session.prepare()
        self.submit(self.auto_ask)

    # -- actions -------------------------------------------------------------
    @objc.python_method
    def toggle(self) -> None:
        log.debug("hotkey tap: panel visible=%s", self.panel.visible)
        if self.panel.visible:
            self.panel.hide()
            return
        self.panel.show()  # excluded from captures, so it can appear right away
        if self.overlay.has_content:
            # The drawing is visible in captures now; take it off screen for the
            # model's screenshot, then put it back. Wait a beat for the window
            # server to drop it before capturing.
            self._hidden_captures += 1
            self.overlay.hide_for_capture()
            AppHelper.callLater(0.08, self._snapshot_then_unhide)
            AppHelper.callLater(2.0, self._unhide_if_stuck)  # never leave the drawing hidden
        else:
            self.session.prepare()

    @objc.python_method
    def _snapshot_then_unhide(self) -> None:
        try:
            snap = self.session.prepare()
        except Exception:
            log.exception("screen snapshot failed")
            snap = None
        if snap is None:
            self._capture_done()
        else:
            snap.add_done_callback(lambda _f: AppHelper.callAfter(self._capture_done))

    @objc.python_method
    def _capture_done(self) -> None:
        # Only the last overlapping capture brings the drawing back, so a rapid
        # re-tap can't put it on screen while the next screenshot is taken.
        self._hidden_captures = max(0, self._hidden_captures - 1)
        if self._hidden_captures == 0:
            self.overlay.unhide()

    @objc.python_method
    def _unhide_if_stuck(self) -> None:
        if self._hidden_captures and not self.overlay.window.isVisible():
            log.warning("snapshot slow; showing the drawing again")
            self._hidden_captures = 0
            self.overlay.unhide()

    @objc.python_method
    def submit(self, text: str) -> None:
        text = text.strip()
        if text in ("/new", "/reset"):
            self.session.reset()
            self.overlay.clear()
        elif text == "/clear":
            self.overlay.clear()
        elif text:
            self.session.submit(text)

    @objc.python_method
    def dismiss(self) -> None:
        log.info("drawing dismissed")
        self.session.cancel()
        self.overlay.clear()

    @objc.python_method
    def escape(self) -> None:
        # Esc clears the drawing when the prompt box isn't open. Clicks never do:
        # the drawing stays until Esc or its ✕ button.
        if not self.panel.visible and self.overlay.has_content:
            self.dismiss()

    # -- menu bar ------------------------------------------------------------
    @objc.python_method
    def _build_menu(self) -> None:
        self.status_item = NSStatusBar.systemStatusBar().statusItemWithLength_(NSVariableStatusItemLength)
        self.status_item.button().setTitle_("◐")
        menu = NSMenu.alloc().init()
        for title, sel, key in (
            ("Ask…  (tap ⌃⌥)", "menuAsk:", ""),
            ("New conversation", "menuNew:", ""),
            ("Clear drawing", "menuClear:", ""),
            (None, None, None),
            ("Quit understanding", "terminate:", "q"),
        ):
            if title is None:
                menu.addItem_(NSMenuItem.separatorItem())
                continue
            item = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, sel, key)
            item.setTarget_(None if sel == "terminate:" else self)
            menu.addItem_(item)
        self.status_item.setMenu_(menu)

    def menuAsk_(self, _sender) -> None:
        self.toggle()

    def menuNew_(self, _sender) -> None:
        self.submit("/new")

    def menuClear_(self, _sender) -> None:
        self.dismiss()


def run(cfg: Config, auto_ask: str | None = None) -> None:
    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    controller = Controller.alloc().initWithConfig_autoAsk_(cfg, auto_ask)
    app.setDelegate_(controller)
    AppHelper.runEventLoop(installInterrupt=True)
