# Roadmap

- [x] v0: ⌃⌥ tap → prompt box → Haiku draws card/diagram/steps/timeline/svg + on-screen pins/boxes; follow-ups in one session; Esc clears
- [x] Text grounding: `quote` on box/pin snaps to OCR'd on-screen text
- [ ] Image grounding: model names a non-text target ("fan blades"), a vision locator (e.g. TypeSafe Jev Box) resolves it instead of trusting model coordinates
- [ ] Verify a hardware Esc clears the drawing while Chrome is frontmost (synthetic Esc didn't arrive)
- [ ] Re-place existing labels when the card flips sides
- [x] 3D primitive: `scene3d`/`part` (three.js), streamed parts, cutaways, callout labels
- [ ] Voice: TTS reads `say` lines in sync with drawing; STT stays Wispr Flow
- [ ] Clickable card (copy text, pin card, ask follow-up by clicking a node)
- [ ] Other brains: Anthropic API direct, local model (Ollama / llama.cpp server)
- [ ] Multi-display: overlay follows the display the question was asked on (partly done)
- [ ] JS test harness; pin `U.findQuote` word-boundary and prefix-floor rules (fable review nit)
- [ ] OCR line grouping by vertical overlap instead of `y // 6` buckets; OCR timeout during first-run compile (fable review nits S4/S5)
- [ ] Quoted-highlight label: on a clash, `placeLabel` mirrors left of the highlight end (onto the text); skip mirrored tries or fall back to above-the-box (fable review nit)
- [ ] Let the user rotate a 3D scene (the overlay is click-through; needs a hit-testable region)
- [ ] scene3d review nits: cut on `axis:"z"` parts keeps the wrong half; gate the prompt's 3D routing on scene3d being enabled; fit() during pop-in can under-size the camera distance
- [ ] Fill the cut plane of cutaway solids (three.js leaves it open, so a cut shaft is a half-shell)
- [ ] Unhide the drawing as soon as the screenshot itself is taken, not after OCR (and per-capture stuck timers); fable review nits N2/N3
