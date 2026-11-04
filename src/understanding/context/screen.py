"""Screenshot of the display the mouse is on, downscaled for the model.

Our own windows set sharingType=None, so they never appear in captures.
"""

from __future__ import annotations

import logging
import subprocess
import time
import tempfile
from pathlib import Path

from understanding.brains import Image
from understanding.context import Contribution, register
from understanding.context.ocr import text_anchors

log = logging.getLogger(__name__)


def _display_index_under_mouse() -> int:
    from AppKit import NSEvent, NSScreen
    from Foundation import NSPointInRect

    mouse = NSEvent.mouseLocation()
    for i, s in enumerate(NSScreen.screens()):
        if NSPointInRect(mouse, s.frame()):
            return i + 1  # screencapture -D is 1-based in NSScreen order
    return 1


@register("screen")
def screen(max_side: int = 1280, quality: int = 70, ocr: bool = True):
    def capture() -> Contribution:
        t0 = time.monotonic()
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
            data = path.read_bytes()
            log.info("screenshot %dx%d %d KB in %.2fs", w, h, len(data) // 1024, time.monotonic() - t0)
            anchors = text_anchors(path, w, h) if ocr else []
            log.info("ocr: %d text anchors, total %.2fs", len(anchors), time.monotonic() - t0)
            return Contribution(images=[Image(data, "image/jpeg", w, h)], anchors=anchors)

    return capture
