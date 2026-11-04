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
- Live (2026-11-03, Retina MacBook, Wikipedia in Chrome): screenshot 0.22–0.27 s, OCR (Vision accurate) +0.1–0.4 s, both done at hotkey time while the user types; first op 0.68–0.78 s after Enter, full answer 1.2–4 s. One outlier: first op 4.8 s (API variance; same question again was 0.74 s).
- OCR: Vision `accurate` warm is 0.08–0.15 s on 1280 px; the first run after install took 25.7 s (one-time model compile, cached by macOS across processes). `fast` mode garbles words ("Wi\ufffdpadia"), so quotes wouldn't match. Budget 1.5 s, then continue without anchors.

## Grounding

Models say WHAT to point at well and WHERE poorly. `box`/`pin` take `"quote"`: exact on-screen words, located in OCR anchors (`context/ocr.py` → `Contribution.anchors` → `U.findQuote`). Before this, Haiku's highlight boxes landed a few lines off and cut through text; with quotes they sit on the real sentence. x/y remains for non-text (parts of an image), where Haiku's points were good (turbofan parts landed on the numbered labels).

## Scars

- 2026-11-03: CSS `zoom` to shrink an overflowing card also shrank its `max-height`, so captions spilled outside the card. Fit uses `transform: scale` on the unconstrained layout height instead.
- 2026-11-03: card side was checked only when a pin was added, while the card was still title-only, so it later grew over the pins. The check now runs on every card resize (ResizeObserver).
- 2026-11-03: headless Chrome screenshots with `--virtual-time-budget=6000` caught animations mid-flight and looked like broken renders. Use 20000.
- 2026-11-03: the prompt panel used `NSVisualEffectView` HUD material; over a dark app it was effectively invisible, so the user thought the app didn't work. It's now a solid dark pill with an amber border.
- 2026-11-03: Return in the prompt field never reached `control:textView:doCommandBySelector:` (PyObjC delegate). Submit uses the field's target/action (`submit:`); Esc uses `cancelOperation:` on the panel.
- 2026-11-03: `NSApp.activateIgnoringOtherApps_` + `prevApp.activateWithOptions_` (deprecated under cooperative activation) left keyboard focus in limbo after the panel closed. The panel is now non-activating (Spotlight pattern): it takes the keyboard without activating the app, and focus returns by itself.
- 2026-11-03: something on Garrett's Mac emits phantom Shift flag changes; the ⌃⌥ release arrived as `{shift}` and cancelled the tap. Shift is ignored unless it's part of the chord (`test_phantom_shift_is_ignored`).
- 2026-11-03: NSEvent global keyDown monitors (and later a listen-only CGEventTap) never saw synthetic Esc (`cliclick`) while Chrome was frontmost, though modifier changes always arrived. No Secure Input holder was found. Unresolved whether a hardware Esc behaves the same; so Esc is not the only dismiss path: a click anywhere (event-tap mouse-down) and Esc inside the prompt box both clear the drawing. The hotkey now uses the event tap instead of NSEvent monitors.
- 2026-11-03: Esc mid-answer cleared the overlay, then ops already queued for the main thread redrew it. `OverlayRenderer` stamps each call with the overlay generation; `clear()` bumps it.
- 2026-11-03 (testing): synthetic modifier combos from `cliclick` sent while driving the live app put Chrome into full screen. When driving the app on the user's Mac, send only the ⌃⌥ tap, plain text, Return, and Esc. Also, never name a probe script after a stdlib module (`bisect.py` broke PyObjC's import chain).
- 2026-11-04 (simulated-user session on the Mac, 3 scenarios): diagram edges that skip a row or column ran straight through the box between (Pi diagram: CPU→microSD through GPIO); they now bow around. Highlight labels sat on the text line above; quoted highlights now label to the right of where the highlight ends. "Show me exactly how" got steps only; the svg doc now asks for a sketch of the key moment. `snapshot` output disables animations so headless screenshots are complete.
- 2026-11-04 (Garrett's photo): the status pill sat 14 px from the screen top, behind the MacBook notch. The overlay now reads the screen's unsafe top band (max of menu-bar height and `safeAreaInsets().top`: 33 pt / 32 pt on his built-in display) and positions the pill and card below it via `--safe-top`.
- 2026-11-04 (Garrett): "detailed 2D diagram of the F135's engines" got a boxes-and-arrows flowchart, and "3D" got a refusal. Causes: nothing told the model that a diagram of a physical thing means drawing it, and there was no 3D primitive. Added `scene3d`/`part` (three.js r159, vendored; the last release with a non-module build, needed because the page is an inline HTML string) and a CHOOSING THE VISUAL section in the prompt. Same questions afterwards: a labeled side-view cutaway SVG, and a 3D cutaway with fan, compressor stages, shaft, combustor, turbine, afterburner (10 parts, under 4 s).
- three.js's build starts with `console.warn('…'),function(t,e){…}(…)`. Cutting at the first `');` removed real code, and dropping only the warn left a statement starting with an anonymous `function`, a syntax error. The vendored file replaces the warn with `void`.
- The scene3d prompt example is a turbofan, and Haiku copies it closely for engine questions. The doc tells it to model the real object's parts; watch for template-y answers on other machines.
