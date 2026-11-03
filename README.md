# understanding

Real-time visual explanations on top of whatever you're looking at. Tap **⌃⌥** (Control + Option, then release), type or dictate a question with Wispr Flow, and press **Enter**. A headless Claude Code session (Haiku by default) looks at your screen and draws the answer live: an explainer card with diagrams, and labels pinned onto the real things on screen. Follow-up questions continue the same conversation.

## Run

```sh
./understanding            # menu-bar app (◐ in the menu bar)
./understanding demo       # same app, canned answer, no model: checks the overlay works
./understanding --model sonnet
```

Requirements: macOS, [uv](https://docs.astral.sh/uv/), and the `claude` CLI logged in.

On first run, grant the app you launch it from (Terminal, iTerm, …):
- **Accessibility**, for the global ⌃⌥ hotkey
- **Screen Recording**, for the screenshot (without it the model sees a black screen)

Both are in System Settings ▸ Privacy & Security. Restart after granting.

## Use

| Action | Does |
| --- | --- |
| tap ⌃⌥ | open or close the prompt box |
| Enter | ask; the box closes and the answer draws itself |
| Esc | close the box, or clear the drawing |
| `/new` | start a new conversation |
| `/clear` | clear the drawing |

## Develop

```sh
./understanding ask "how does this work?"                  # headless: prints ops as they stream
./understanding ask --image shot.jpg "label the parts" > ops.txt
./understanding snapshot ops.txt --image shot.jpg --out out.html   # see the render in a browser
./understanding prompt                                     # the composed system prompt
uv run pytest
```

Logs: `~/Library/Logs/understanding.log` (includes renderer JS errors). The overlay's webview can be inspected from Safari ▸ Develop.

Config lives in `~/.config/understanding/config.toml`:

```toml
brain_options = { model = "haiku", effort = "low" }   # any claude --model value
context = ["screen", "frontmost_app"]
primitives = []          # empty = all
prompt_extra = "Explain like I'm an engineer."
hotkey = ["control", "option"]
```

Architecture and extension points: [`ai/README.md`](ai/README.md).
