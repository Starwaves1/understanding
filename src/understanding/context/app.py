"""Name and window title of the frontmost app: cheap, high-signal context."""

from __future__ import annotations

from understanding.context import Contribution, register


@register("frontmost_app")
def frontmost_app():
    def capture() -> Contribution:
        from AppKit import NSWorkspace
        from Quartz import (
            CGWindowListCopyWindowInfo,
            kCGNullWindowID,
            kCGWindowListExcludeDesktopElements,
            kCGWindowListOptionOnScreenOnly,
        )

        app = NSWorkspace.sharedWorkspace().frontmostApplication()
        if app is None:
            return Contribution()
        name, pid = app.localizedName(), app.processIdentifier()
        title = ""
        windows = CGWindowListCopyWindowInfo(
            kCGWindowListOptionOnScreenOnly | kCGWindowListExcludeDesktopElements, kCGNullWindowID
        )
        for w in windows or []:
            if w.get("kCGWindowOwnerPID") == pid and w.get("kCGWindowLayer") == 0 and w.get("kCGWindowName"):
                title = w["kCGWindowName"]
                break
        note = f"Frontmost app: {name}" + (f' — window "{title}"' if title else "")
        return Contribution(notes=[note])

    return capture
