# Roadmap

- [x] v0: ⌃⌥ tap → prompt box → Haiku draws card/diagram/steps/timeline/svg + on-screen pins/boxes; follow-ups in one session; Esc clears
- [ ] Grounded pins: model names a target (`"target":"fan blades"`), a grounding module resolves it with a vision locator (e.g. TypeSafe Jev Box) instead of trusting model coordinates
- [ ] Re-place existing labels when the card flips sides
- [ ] 3D primitive (three.js scene spec) — the video's "draw the full jet in 3D"
- [ ] Voice: TTS reads `say` lines in sync with drawing; STT stays Wispr Flow
- [ ] Clickable card (copy text, pin card, ask follow-up by clicking a node)
- [ ] Other brains: Anthropic API direct, local model (Ollama / llama.cpp server)
- [ ] Multi-display: overlay follows the display the question was asked on (partly done)
