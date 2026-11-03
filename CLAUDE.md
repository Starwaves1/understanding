# understanding

Tap ⌃⌥, ask about your screen, and a headless Claude (Haiku by default) draws the answer live as an overlay: explainer card, diagrams, and labels pinned onto the real screen.

Read `ai/README.md` before changing any subsystem. When you learn something the code can't say (a dead end, a measured number), write it into the matching `ai/` doc in the same change.

Damage gates:
- Run from source with `./understanding`, not `uv run understanding`: iCloud-synced folders re-hide uv's editable `.pth`, and Python 3.13 skips hidden `.pth` files.
- Methods on PyObjC `NSObject` subclasses become ObjC selectors. Mark Python-only helpers `@objc.python_method`, or class creation fails.
- Never push `--force` to `main`.
