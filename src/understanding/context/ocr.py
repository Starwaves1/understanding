"""On-device text recognition (macOS Vision) for grounding.

The model is good at saying WHAT to highlight and poor at pixel-exact
coordinates, so it quotes on-screen text and the renderer looks the quote up
in these anchors. Accurate mode takes ~0.1 s warm on a 1280 px screenshot.
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from pathlib import Path

log = logging.getLogger(__name__)
_pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ocr")


def _recognize(path: Path, width: int, height: int) -> list[dict]:
    import Quartz
    import Vision
    from Foundation import NSURL

    src = Quartz.CGImageSourceCreateWithURL(NSURL.fileURLWithPath_(str(path)), None)
    img = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(0)  # accurate; fast mode garbles words ("Wi�padia")
    req.setUsesLanguageCorrection_(False)
    Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(img, None).performRequests_error_([req], None)
    anchors = []
    for obs in req.results() or []:
        text = obs.topCandidates_(1)[0].string()
        b = obs.boundingBox()  # normalized, origin bottom-left
        anchors.append(
            {
                "t": str(text),
                "x": round(b.origin.x * width),
                "y": round((1 - b.origin.y - b.size.height) * height),
                "w": round(b.size.width * width),
                "h": round(b.size.height * height),
            }
        )
    anchors.sort(key=lambda a: (a["y"] // 6, a["x"]))  # reading order, tolerant of jitter
    return anchors


def text_anchors(path: Path, width: int, height: int, budget: float = 1.5) -> list[dict]:
    """Anchors in screenshot pixels, or [] if OCR fails or exceeds its budget."""
    try:
        return _pool.submit(_recognize, path, width, height).result(timeout=budget)
    except FutureTimeout:
        log.warning("OCR exceeded %.1fs budget; continuing without text anchors", budget)
    except Exception:
        log.exception("OCR failed")
    return []
