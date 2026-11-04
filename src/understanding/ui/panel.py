"""The floating prompt box: type or dictate (Wispr Flow), Enter to ask, Esc to dismiss."""

from __future__ import annotations

import logging
from collections.abc import Callable

from AppKit import (
    NSBackingStoreBuffered,
    NSColor,
    NSFont,
    NSMakeRect,
    NSPanel,
    NSTextField,
    NSView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import NSObject

from understanding.ui.overlay import NSWindowSharingNone, screen_under_mouse

log = logging.getLogger(__name__)
W, H = 720, 64
PANEL_LEVEL = 1001


class KeyPanel(NSPanel):
    """Borderless panels refuse key status by default; we need the keyboard."""

    owner = None

    def canBecomeKeyWindow(self) -> bool:
        return True

    # Esc in the text field travels up the responder chain to here.
    def cancelOperation_(self, _sender) -> None:
        if self.owner is not None:
            self.owner.on_escape()


class _Target(NSObject):
    """Receives the text field's action, which AppKit sends on Return."""

    owner = None

    def submit_(self, _sender) -> None:
        log.debug("field action fired, owner=%s", self.owner)
        if self.owner is not None:
            self.owner.on_enter()


def _rgba(r: float, g: float, b: float, a: float):
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, a).CGColor()


class PromptPanel:
    def __init__(self, on_submit: Callable[[str], None], on_escape: Callable[[], None]) -> None:
        self._on_submit = on_submit
        self._on_escape = on_escape
        p = KeyPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, W, H),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        p.owner = self
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(True)
        p.setLevel_(PANEL_LEVEL)
        p.setSharingType_(NSWindowSharingNone)
        p.setHidesOnDeactivate_(False)
        p.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        # Solid, high-contrast pill: a translucent material vanished over dark apps.
        bg = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
        bg.setWantsLayer_(True)
        layer = bg.layer()
        layer.setCornerRadius_(18)
        layer.setBackgroundColor_(_rgba(0.11, 0.11, 0.12, 0.98))
        layer.setBorderWidth_(1.5)
        layer.setBorderColor_(_rgba(0.94, 0.71, 0.16, 0.9))  # same amber as the overlay accent
        p.setContentView_(bg)

        icon = NSTextField.labelWithString_("◐")
        icon.setFont_(NSFont.systemFontOfSize_(22))
        icon.setTextColor_(NSColor.colorWithSRGBRed_green_blue_alpha_(0.94, 0.71, 0.16, 1))
        icon.setFrame_(NSMakeRect(18, 17, 28, 30))
        bg.addSubview_(icon)

        f = NSTextField.alloc().initWithFrame_(NSMakeRect(52, 18, W - 72, 28))
        f.setBezeled_(False)
        f.setDrawsBackground_(False)
        f.setFocusRingType_(1)  # none
        f.setFont_(NSFont.systemFontOfSize_(20))
        f.setTextColor_(NSColor.whiteColor())
        f.setPlaceholderString_("Ask about your screen…    ⏎ ask · esc close · /new resets")
        f.cell().setScrollable_(True)
        f.cell().setWraps_(False)
        self._target = _Target.alloc().init()
        self._target.owner = self
        f.setTarget_(self._target)
        f.setAction_("submit:")
        bg.addSubview_(f)
        self.panel, self.field = p, f

    @property
    def visible(self) -> bool:
        return bool(self.panel.isVisible())

    def show(self) -> None:
        sf = screen_under_mouse().visibleFrame()
        x = sf.origin.x + (sf.size.width - W) / 2
        y = sf.origin.y + sf.size.height * 0.78
        self.panel.setFrameOrigin_((x, y))
        self.field.setStringValue_("")
        # A non-activating panel takes the keyboard without activating our app
        # (the Spotlight pattern): the user's app stays active and gets focus
        # back by itself on close. Activating and re-activating the previous app
        # left keyboard focus in limbo on macOS 26+ (Esc stopped arriving).
        self.panel.makeKeyAndOrderFront_(None)
        self.panel.makeFirstResponder_(self.field)

    def hide(self) -> None:
        self.panel.orderOut_(None)

    def on_enter(self) -> None:
        text = str(self.field.stringValue())
        log.debug("prompt submitted: %r", text)
        self.hide()
        self._on_submit(text)

    def on_escape(self) -> None:
        self.hide()
        self._on_escape()

