"""Full-screen, transparent, click-through window hosting the HTML renderer."""

from __future__ import annotations

import json
import os
from pathlib import Path

from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSEvent,
    NSScreen,
    NSWindow,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowCollectionBehaviorStationary,
    NSWindowStyleMaskBorderless,
)
from Foundation import NSURL, NSObject, NSPointInRect
from PyObjCTools.AppHelper import callAfter
from WebKit import WKUserScript, WKWebView, WKWebViewConfiguration

import logging

log = logging.getLogger(__name__)
WKUserScriptInjectionTimeAtDocumentStart = 0

# Forward renderer errors to the Python log (~/Library/Logs/understanding.log).
_JS_LOG_BRIDGE = """
(() => {
  const post = (level, args) => window.webkit.messageHandlers.log.postMessage(
    level + ": " + args.map((a) => (a && a.stack) || (typeof a === "object" ? JSON.stringify(a) : String(a))).join(" "));
  for (const level of ["error", "warn"]) {
    const orig = console[level];
    console[level] = (...args) => { post(level, args); orig.apply(console, args); };
  }
  window.addEventListener("error", (e) => post("error", [e.message + " @" + e.lineno]));
})();
"""


class _JSLog(NSObject):
    def userContentController_didReceiveScriptMessage_(self, _controller, message) -> None:
        log.warning("renderer %s", message.body())

from understanding.primitives import Primitive
from understanding.protocol import Op

WEB = Path(__file__).resolve().parent.parent / "web"
OVERLAY_LEVEL = 1000  # above normal and floating windows, below our prompt panel
NSWindowSharingNone = 0
NSWindowSharingReadOnly = 1
# UNDERSTANDING_CAPTURABLE=1 lets our windows show up in screenshots (debugging,
# sharing a demo). Off by default so the screen context never sees our drawings.
SHARING = NSWindowSharingReadOnly if os.environ.get("UNDERSTANDING_CAPTURABLE") else NSWindowSharingNone


def build_html(primitives: list[Primitive]) -> str:
    html = (WEB / "overlay.html").read_text()
    scripts = "\n".join(f"<script>/* {p.name} */\n{p.js}\n</script>" for p in primitives if p.js)
    return (
        html.replace("/*CSS*/", (WEB / "overlay.css").read_text())
        .replace("/*RUNTIME*/", (WEB / "runtime.js").read_text())
        .replace("<!--PRIMITIVES-->", scripts)
    )


def screen_under_mouse():
    mouse = NSEvent.mouseLocation()
    for s in NSScreen.screens():
        if NSPointInRect(mouse, s.frame()):
            return s
    return NSScreen.mainScreen()


class Overlay:
    """Main-thread only. OverlayRenderer is the thread-safe front door."""

    def __init__(self, primitives: list[Primitive]) -> None:
        screen = screen_under_mouse()
        self.window = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            screen.frame(), NSWindowStyleMaskBorderless, NSBackingStoreBuffered, False
        )
        w = self.window
        w.setOpaque_(False)
        w.setBackgroundColor_(NSColor.clearColor())
        w.setHasShadow_(False)
        w.setIgnoresMouseEvents_(True)
        w.setLevel_(OVERLAY_LEVEL)
        w.setSharingType_(SHARING)  # keep our drawings out of the screenshots
        w.setReleasedWhenClosed_(False)
        w.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces
            | NSWindowCollectionBehaviorFullScreenAuxiliary
            | NSWindowCollectionBehaviorStationary
        )
        cfg = WKWebViewConfiguration.alloc().init()
        self._js_log = _JSLog.alloc().init()
        ucc = cfg.userContentController()
        ucc.addScriptMessageHandler_name_(self._js_log, "log")
        ucc.addUserScript_(
            WKUserScript.alloc().initWithSource_injectionTime_forMainFrameOnly_(
                _JS_LOG_BRIDGE, WKUserScriptInjectionTimeAtDocumentStart, True
            )
        )
        self.web = WKWebView.alloc().initWithFrame_configuration_(w.contentView().bounds(), cfg)
        self.web.setValue_forKey_(False, "drawsBackground")
        self.web.setAutoresizingMask_(18)  # width + height sizable
        if hasattr(self.web, "setInspectable_"):
            self.web.setInspectable_(True)  # Safari ▸ Develop ▸ <host> to debug the renderer
        w.contentView().addSubview_(self.web)
        self.web.loadHTMLString_baseURL_(build_html(primitives), NSURL.fileURLWithPath_(str(WEB) + "/"))
        w.orderFrontRegardless()
        self.has_content = False
        # Bumped by clear(). Ops already queued for the main thread carry the
        # generation they were sent under and are dropped if it has moved on,
        # so Esc mid-answer can't be undone by stragglers.
        self.generation = 0

    def js(self, code: str) -> None:
        self.web.evaluateJavaScript_completionHandler_(code, None)

    def follow_mouse_screen(self) -> None:
        frame = screen_under_mouse().frame()
        if frame != self.window.frame():
            self.window.setFrame_display_(frame, True)
        self.window.orderFrontRegardless()

    def clear(self) -> None:
        self.generation += 1
        self.has_content = False
        self.js("U.clear(); U.status(null)")


class OverlayRenderer:
    """Session Renderer that marshals every call onto the main thread."""

    def __init__(self, overlay: Overlay) -> None:
        self.overlay = overlay
        self._box = [-1]  # [generation of the current turn], filled in on the main thread

    def _send(self, code: str, turn_gen_box: list[int]) -> None:
        def run() -> None:
            if turn_gen_box[0] == self.overlay.generation:
                self.overlay.js(code)

        callAfter(run)

    def begin(self, question: str, frame: tuple[int, int] | None, anchors: list[dict]) -> None:
        imgW, imgH = frame or (0, 0)
        payload = json.dumps({"question": question[:120], "imgW": imgW, "imgH": imgH, "anchors": anchors})
        box = self._box = [-1]

        def run() -> None:
            # A new turn starts a new generation; earlier stragglers die.
            self.overlay.generation += 1
            box[0] = self.overlay.generation
            self.overlay.follow_mouse_screen()
            self.overlay.has_content = True
            self.overlay.js(f"U.begin({payload})")

        callAfter(run)

    def apply(self, op: Op) -> None:
        self._send(f"U.apply({json.dumps(op)})", self._box)

    def end(self, error: str | None) -> None:
        self._send(f"U.end({json.dumps(error)})", self._box)
