# Roadmap

- [x] v0: ⌃⌥ tap → prompt box → Haiku draws card/diagram/steps/timeline/svg + on-screen pins/boxes; follow-ups in one session; Esc clears
- [x] Text grounding: `quote` on box/pin snaps to OCR'd on-screen text
- [ ] Image grounding: model names a non-text target ("fan blades"), a vision locator (e.g. TypeSafe Jev Box) resolves it instead of trusting model coordinates
- [ ] Verify a hardware Esc clears the drawing while Chrome is frontmost (synthetic Esc didn't arrive)
- [ ] Re-place existing labels when the card flips sides
- [ ] 3D primitive (three.js scene spec) — the video's "draw the full jet in 3D"
- [ ] Voice: TTS reads `say` lines in sync with drawing; STT stays Wispr Flow
- [ ] Clickable card (copy text, pin card, ask follow-up by clicking a node)
- [ ] Other brains: Anthropic API direct, local model (Ollama / llama.cpp server)
- [ ] Multi-display: overlay follows the display the question was asked on (partly done)
