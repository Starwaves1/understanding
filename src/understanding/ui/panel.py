"""The floating prompt box: type or dictate (Wispr Flow), Enter to ask, Esc to dismiss."""

from __future__ import annotations

import os
from collections.abc import Callable

import objc
from AppKit import (
    NSApp,
    NSBackingStoreBuffered,
    NSColor,
    NSFont,
    NSMakeRect,
    NSPanel,
    NSTextField,
    NSVisualEffectBlendingModeBehindWindow,
    NSVisualEffectMaterialHUDWindow,
    NSVisualEffectStateActive,
    NSVisualEffectView,
    NSWindowCollectionBehaviorCanJoinAllSpaces,
    NSWindowCollectionBehaviorFullScreenAuxiliary,
    NSWindowStyleMaskBorderless,
    NSWindowStyleMaskNonactivatingPanel,
)
from Foundation import NSObject

from understanding.ui.overlay import NSWindowSharingNone, screen_under_mouse

W, H = 680, 58
PANEL_LEVEL = 1001


class KeyPanel(NSPanel):
    def canBecomeKeyWindow(self) -> bool:
        return True


class _FieldDelegate(NSObject):
    def initWithPanel_(self, panel):
        self = objc.super(_FieldDelegate, self).init()
        self.panel = panel
        return self

    def control_textView_doCommandBySelector_(self, control, text_view, selector) -> bool:
        sel = selector.decode() if isinstance(selector, bytes) else str(selector)
        if sel == "cancelOperation:":
            self.panel.on_escape()
            return True
        if sel == "insertNewline:":
            self.panel.on_enter()
            return True
        return False


class PromptPanel:
    def __init__(self, on_submit: Callable[[str], None], on_escape: Callable[[], None]) -> None:
        self._on_submit = on_submit
        self._on_escape = on_escape
        self._prev_app = None
        p = KeyPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(0, 0, W, H),
            NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
            NSBackingStoreBuffered,
            False,
        )
        p.setOpaque_(False)
        p.setBackgroundColor_(NSColor.clearColor())
        p.setHasShadow_(True)
        p.setLevel_(PANEL_LEVEL)
        p.setSharingType_(NSWindowSharingNone)
        p.setHidesOnDeactivate_(False)
        p.setCollectionBehavior_(
            NSWindowCollectionBehaviorCanJoinAllSpaces | NSWindowCollectionBehaviorFullScreenAuxiliary
        )
        fx = NSVisualEffectView.alloc().initWithFrame_(NSMakeRect(0, 0, W, H))
        fx.setMaterial_(NSVisualEffectMaterialHUDWindow)
        fx.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
        fx.setState_(NSVisualEffectStateActive)
        fx.setWantsLayer_(True)
        fx.layer().setCornerRadius_(16)
        fx.layer().setMasksToBounds_(True)
        p.setContentView_(fx)

        f = NSTextField.alloc().initWithFrame_(NSMakeRect(20, 14, W - 40, 30))
        f.setBezeled_(False)
        f.setDrawsBackground_(False)
        f.setFocusRingType_(1)  # none
        f.setFont_(NSFont.systemFontOfSize_(20))
        f.setTextColor_(NSColor.whiteColor())
        f.setPlaceholderString_("Ask about your screen…   (Enter to ask · Esc to close · /new resets)")
        f.cell().setScrollable_(True)
        f.cell().setWraps_(False)
        self._delegate = _FieldDelegate.alloc().initWithPanel_(self)
        f.setDelegate_(self._delegate)
        fx.addSubview_(f)
        self.panel, self.field = p, f

    @property
    def visible(self) -> bool:
        return bool(self.panel.isVisible())

    def show(self) -> None:
        from AppKit import NSWorkspace

        front = NSWorkspace.sharedWorkspace().frontmostApplication()
        if front is not None and front.processIdentifier() != os.getpid():
            self._prev_app = front
        sf = screen_under_mouse().visibleFrame()
        x = sf.origin.x + (sf.size.width - W) / 2
        y = sf.origin.y + sf.size.height * 0.80
        self.panel.setFrameOrigin_((x, y))
        self.field.setStringValue_("")
        NSApp.activateIgnoringOtherApps_(True)
        self.panel.makeKeyAndOrderFront_(None)
        self.panel.makeFirstResponder_(self.field)

    def hide(self, restore_focus: bool = True) -> None:
        self.panel.orderOut_(None)
        if restore_focus and self._prev_app is not None:
            self._prev_app.activateWithOptions_(0)

    def on_enter(self) -> None:
        text = str(self.field.stringValue())
        self.hide()
        self._on_submit(text)

    def on_escape(self) -> None:
        self.hide()
        self._on_escape()
