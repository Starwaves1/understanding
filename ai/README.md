# Architecture router

## Pipeline

```
hotkey (ui/hotkey.py) ──tap──▶ Session.prepare(): context providers snapshot the screen in parallel
prompt panel (ui/panel.py) ──Enter──▶ Session.submit(question)
Session worker thread (session.py):
    Turn(question, images, notes) ─▶ Brain.stream()  ─ text deltas ─▶ OpStreamParser (protocol.py)
                                                                       │ one op per completed JSONL line
                                                                       ▼
                                   Renderer.apply(op) ─▶ OverlayRenderer ─main thread─▶ WKWebView: U.apply(op)
                                                                                         └ primitives/<name>.js
```

## Extension points (the modular surface)

| Want to… | Touch | Contract |
| --- | --- | --- |
| Use a different model or backend (local LLM, raw API) | `brains/<name>.py` + `@register("<name>")` | `Brain` protocol in `brains/__init__.py`: `start / stream(turn) -> Iterator[str] / interrupt / reset / close` |
| Add context (clipboard, browser URL, selected text, OCR) | `context/<name>.py` + `@register` | factory returns `() -> Contribution(images, notes)`; runs at hotkey time, in parallel |
| Add a visual primitive (chart, 3D scene, math) | `primitives/<name>.md` + `<name>.js`, or the same pair in `~/.config/understanding/primitives/` | `.md` is the prompt doc (must show an example op line); `.js` calls `U.register("<op>", (op, U) => …)`. Screen-drawing primitives call `U.mark(rect)` and `U.placeLabel(...)` so the card and labels avoid them |
| Change UI shell (other OS, different trigger) | `ui/`, `app.py` | `Session` only needs a `Renderer` (`begin / apply / end`) |
| Test without the overlay | `./understanding ask --image f.jpg "q"` then `./understanding snapshot ops.txt --image f.jpg` → HTML | |

Config: `~/.config/understanding/config.toml`, keys = fields of `config.Config`.

## Settled principles

- **Stream ops, not documents.** The model emits JSON Lines; each line renders the instant it completes. Never buffer a whole answer.
- **Layout is the renderer's job, not the model's.** The model gives intent (grid cell, point to label, preferred side); the runtime fixes collisions (card flips away from marks, labels dodge each other). Haiku's pointing is decent, its layout judgment is not.
- **One warm brain process per conversation.** Follow-ups reuse it; `/new` respawns.
- **Our windows set `sharingType = none`**, so screenshots never contain our own drawings and the snapshot can be taken at any time.

## Values with provenance (measured 2026-11-03, Haiku 5.5, M-series Mac)

- `MAX_THINKING_TOKENS=0` + `--effort low` (brain defaults `thinking=False`, `effort="low"`). With default thinking, first op took **7.0 s**; effort low alone 0.6–3.3 s; thinking off **0.40–0.52 s** every turn. Do not re-enable thinking by default.
- Warm-up turn at spawn: the first message to a fresh `claude -p` pays ~2.5 s one-time setup. `ClaudeCodeBrain.start()` spends it before the user asks.
- `--setting-sources "" --strict-mcp-config --tools ""`: user hooks/plugins/CLAUDE.md inject context that breaks the JSONL protocol and add startup time.
- Interrupt = `{"type":"control_request","request":{"subtype":"interrupt"}}` on stdin; returns `result` with subtype `error_during_execution`, and the process stays usable for the next turn.
- Screenshot downscaled to max 1280 px (`context/screen.py`); coordinates in ops are in that image's pixels and mapped by `U.sx/U.sy`.

## Scars

- 2026-11-03: CSS `zoom` to shrink an overflowing card also shrank its `max-height`, so captions spilled outside the card. Fit uses `transform: scale` on the unconstrained layout height instead.
- 2026-11-03: card side was checked only when a pin was added, while the card was still title-only, so it later grew over the pins. The check now runs on every card resize (ResizeObserver).
- 2026-11-03: headless Chrome screenshots with `--virtual-time-budget=6000` caught animations mid-flight and looked like broken renders. Use 20000.
