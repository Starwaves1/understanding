"""Full-screen, transparent, click-through window hosting the HTML renderer."""

from __future__ import annotations

import json
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


class _JSLayout(NSObject):
    """Receives the card's viewport rect (or null) so the close button can follow it."""

    overlay = None

    def userContentController_didReceiveScriptMessage_(self, _controller, message) -> None:
        if self.overlay is not None:
            self.overlay.card_moved(message.body())


class _CloseTarget(NSObject):
    callback = None

    def close_(self, _sender) -> None:
        if self.callback is not None:
            self.callback()

from understanding.primitives import Primitive
from understanding.protocol import Op

WEB = Path(__file__).resolve().parent.parent / "web"
OVERLAY_LEVEL = 1000  # above normal and floating windows, below our prompt panel
NSWindowSharingNone = 0
NSWindowSharingReadOnly = 1
CLOSE_SIZE = 30


def build_html(primitives: list[Primitive]) -> str:
    html = (WEB / "overlay.html").read_text()
    # Vendored libraries (three.js for scene3d) load before the primitives that use them.
    vendor = "\n".join(f"<script>{f.read_text()}</script>" for f in sorted((WEB / "vendor").glob("*.js")))
    scripts = vendor + "\n" + "\n".join(f"<script>/* {p.name} */\n{p.js}\n</script>" for p in primitives if p.js)
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
        # Visible in the user's screenshots and recordings. Our own screenshot for
        # the model hides the window first (Overlay.hide_for_capture).
        w.setSharingType_(NSWindowSharingReadOnly)
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
        self._js_layout = _JSLayout.alloc().init()
        self._js_layout.overlay = self
        ucc.addScriptMessageHandler_name_(self._js_layout, "layout")
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
        self.safe_top = 38.0
        self._close = self._make_close_button()
        self.on_close = None  # set by the app: what the ✕ button does
        # Bumped by clear(). Ops already queued for the main thread carry the
        # generation they were sent under and are dropped if it has moved on,
        # so Esc mid-answer can't be undone by stragglers.
        self.generation = 0

    def _make_close_button(self):
        """A tiny clickable window over the card's corner. The overlay itself stays
        click-through, so a click on ✕ never leaks into the app underneath."""
        from AppKit import NSButton, NSMakeRect, NSPanel, NSWindowStyleMaskNonactivatingPanel

        p = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, CLOSE_SIZE, CLOSE_SIZE),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setLevel_(OVERLAY_LEVEL + 1)
        p.setHidesOnDeactivate_(False)
        p.setSharingType_(NSWindowSharingReadOnly)
        p.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        b = NSButton.alloc().initWithFrame_(NSMakeRect(0, 0, CLOSE_SIZE, CLOSE_SIZE))
        b.setBordered_(False)
        b.setWantsLayer_(True)
        b.layer().setCornerRadius_(CLOSE_SIZE / 2)
        b.layer().setBackgroundColor_(NSColor.colorWithSRGBRed_green_blue_alpha_(0.17, 0.16, 0.15, 0.9).CGColor())
        from AppKit import NSAttributedString, NSFont, NSForegroundColorAttributeName, NSFontAttributeName

        b.setAttributedTitle_(
            NSAttributedString.alloc().initWithString_attributes_(
                "✕", {NSForegroundColorAttributeName: NSColor.whiteColor(), NSFontAttributeName: NSFont.boldSystemFontOfSize_(14)}
            )
        )
        b.setToolTip_("Close (Esc)")
        self._close_target = _CloseTarget.alloc().init()
        self._close_target.callback = lambda: self.on_close and self.on_close()
        b.setTarget_(self._close_target)
        b.setAction_("close:")
        p.setContentView_(b)
        return p

    def card_moved(self, rect) -> None:
        """Pin the ✕ to the card's top-right corner (viewport coords → screen)."""
        if not self.has_content or not self.window.isVisible():
            self._close.orderOut_(None)
            return
        f = self.window.frame()
        if rect:
            cx = f.origin.x + float(rect["x"]) + float(rect["w"]) - 6
            cy = f.origin.y + f.size.height - float(rect["y"]) + 6
        else:  # drawing with no card (only screen labels): top center, under the menu bar
            cx = f.origin.x + f.size.width / 2
            cy = f.origin.y + f.size.height - self.safe_top - 60
        self._close.setFrameOrigin_((cx - CLOSE_SIZE / 2, cy - CLOSE_SIZE / 2))
        self._close.orderFrontRegardless()

    def hide_for_capture(self) -> None:
        """Take our drawing off screen while the model's screenshot is taken."""
        self.window.orderOut_(None)
        self._close.orderOut_(None)

    def unhide(self) -> None:
        self.window.orderFrontRegardless()
        if self.has_content:
            self.js("U.reportLayout()")

    def js(self, code: str) -> None:
        self.web.evaluateJavaScript_completionHandler_(code, None)

    def follow_mouse_screen(self) -> float:
        """Move onto the mouse's screen; return its unsafe top band in points
        (menu bar, and the camera notch on MacBooks), which we must draw below."""
        screen = screen_under_mouse()
        frame = screen.frame()
        if frame != self.window.frame():
            self.window.setFrame_display_(frame, True)
        self.window.orderFrontRegardless()
        menu_bar = (frame.origin.y + frame.size.height) - (screen.visibleFrame().origin.y + screen.visibleFrame().size.height)
        notch = screen.safeAreaInsets().top if hasattr(screen, "safeAreaInsets") else 0
        self.safe_top = max(menu_bar, notch, 0)
        return self.safe_top

    def clear(self) -> None:
        self.generation += 1
        self.has_content = False
        self._close.orderOut_(None)
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
            safe_top = self.overlay.follow_mouse_screen()
            self.overlay.has_content = True
            self.overlay.js(f"U.setSafeTop({safe_top:.0f}); U.begin({payload})")

        callAfter(run)

    def apply(self, op: Op) -> None:
        self._send(f"U.apply({json.dumps(op)})", self._box)

    def end(self, error: str | None) -> None:
        self._send(f"U.end({json.dumps(error)})", self._box)
