"""Screenshot of the display the mouse is on, downscaled for the model.

Our own windows set sharingType=None, so they never appear in captures.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from understanding.brains import Image
from understanding.context import Contribution, register


def _display_index_under_mouse() -> int:
    from AppKit import NSEvent, NSScreen
    from Foundation import NSPointInRect

    mouse = NSEvent.mouseLocation()
    for i, s in enumerate(NSScreen.screens()):
        if NSPointInRect(mouse, s.frame()):
            return i + 1  # screencapture -D is 1-based in NSScreen order
    return 1


@register("screen")
def screen(max_side: int = 1280, quality: int = 70):
    def capture() -> Contribution:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "shot.jpg"
            subprocess.run(
                ["screencapture", "-x", "-t", "jpg", "-D", str(_display_index_under_mouse()), str(path)],
                check=True,
                timeout=5,
            )
            subprocess.run(
                ["sips", "-Z", str(max_side), "-s", "formatOptions", str(quality), str(path)],
                check=True,
                capture_output=True,
                timeout=5,
            )
            out = subprocess.run(
                ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(path)],
                check=True, capture_output=True, text=True, timeout=5,
            ).stdout
            w = int(out.split("pixelWidth:")[1].split()[0])
            h = int(out.split("pixelHeight:")[1].split()[0])
            return Contribution(images=[Image(path.read_bytes(), "image/jpeg", w, h)])

    return capture
