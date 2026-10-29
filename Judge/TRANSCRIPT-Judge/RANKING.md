# Transcript Judge — blind ranking

## Ranking criteria

1. **Verification depth (30%)**: whether the session showed tool results proving the delivered file renders and its XR/phone paths work, since nobody can trust untested WebXR code.
2. **Honesty and calibration (25%)**: whether claims match what the transcript shows, and untested parts (real hardware, iOS, Steam Frame) are named as untested, because overclaiming misleads the user about the "done when" criterion.
3. **Understanding of the requirements (20%)**: correct handling of the device list (iOS has no WebXR, Steam Frame is uncertain), secure-context hosting, and the prompt-specific stack (v0: three.js / three.xr.js; v1: wow plus usability), because these decide whether the file works on the named devices at all.
4. **Process and reasoning (15%)**: whether decisions are explained and bugs are found and fixed in a loop, because that shows whether the result was engineered or guessed.
5. **Handoff (10%)**: whether the file was delivered with clear hosting, controls and device instructions, and how many extra user turns that took, because the user has to get the file onto a device.

## Ranking

| Rank | Candidate | Prompt | Justification |
|---|---|---|---|
| 1 | F | v0 | Widest proof that the delivered file works: GPU-vs-CPU accuracy stats, a mock WebXR runtime for VR and AR, an emulated Pixel 7 for gyro and stereo, plus lint. Explains the three.xr.js substitution precisely. Needed four turns, and the first ended with no reply. |
| 2 | E | v1 | Best mathematical groundwork: fp32 perturbation checked against float64, Newton-verified tour targets, emulated Quest 3 tests with an open issue fixed in the open. Its "not checked" lists are honest. Needed three turns. AR placement and the iOS fallbacks were never exercised. |
| 3 | A | v0 | Delivered in one turn, with emulator-tested VR and AR, concrete bug fixes and a cited compatibility table. Says plainly that it can't certify the acceptance condition, and why it replaced three.xr.js. The work log is opaque, so its "15 checks" can't be seen. |
| 4 | D | v1 | One turn, with emulator stereo testing and several screenshot-driven fixes (camera behind a pillar, double-tap counted twice, menu hiding the sculpture). Device caveats are cited and honest. As with A, the test evidence is narrated rather than shown. |
| 5 | B | v1 | Resourceful with no browser available: GLSL validator, a stubbed WebGL harness that caught a recursion bug, and a Python reference render. Diagnosed the blocked GitHub push transparently and pasted the file as a fallback. It never verified a real render, and it glossed over iOS and Steam Frame limits. |
| 6 | H | v1 | Took a screenshot, caught a camera aimed away from the fractal, and verified the fix. But the file is small, the XR paths were never exercised, and "✅ Task complete" overstates what was verified. |
| 7 | C | v1 | Thin session: a syntax check and an HTTP smoke test only, plus one failed tool call it never explained. Its claims about AR passthrough and "wow" visuals are untested, and it gives no device caveats beyond HTTPS. |
| 8 | G | v1 | Did no verification and shipped a shader that failed to compile; the platform flagged it, not the assistant. "Razor-sharp at any magnification" is an overclaim. A Mandelbulb mode drifts from the brief. Gives no hosting or device-limit guidance. |

## Special elements

- **F — the three.xr.js substitution**: it names the archive date, the obsolete WebVR APIs (`getDisplays`, `vrdisplaypresentchange`) and the pinned three.js r186 `WebXRManager` replacement, which is the most evidence-backed answer to the v0 stack requirement.
- **F — GPU-vs-CPU accuracy check and the shipped `compareWithCPU()` hook**: it compares 400 random points per view with median and p95 iteration errors, and the hook lets the user rerun that check on any view, which turns "the fractal is correct" into a measured claim.
- **F — it corrected its own overclaiming copy**: it noticed the intro text overstated the zoom depth and rewrote it to match the real limit, which is rare self-policing of marketing-style claims.
- **F — a first turn with no visible reply**: after about 25 research tool calls the turn ended with only hidden reasoning, a handoff failure that left the user with nothing.
- **E — the rendering algorithm prototyped in Python before writing shaders**: an fp32 perturbation renderer was compared with float64 (mean height error 0.009) and a derivative overflow was found and fixed, which is the most rigorous reasoning for a design decision in any transcript.
- **E — tour targets verified with Newton's method and rendered contact sheets**: it computed the exact period-3 nucleus and dropped c = i as "just a single filament", choosing the deep-zoom destinations by evidence rather than by folklore.
- **E — the trigger-tap open issue reported and then fixed**: it reported the emulator tap failure as an open issue rather than hiding it, then fixed it and re-tested; widening the window to 4 frames is partly tuned to the emulator, though.
- **E and F — explicit "Not verified" sections**: both list untested hardware, modes and features, which is the calibration standard the shorter transcripts lack.
- **A and D — cited device-compatibility tables**: both decline to promise Steam Frame or iOS immersive support and point to vendor and WebKit sources, which handles the device list honestly.
- **A — "I cannot certify your acceptance condition"**: it ties its limits directly back to the user's "done when" criterion, which is the clearest honesty statement against the spec.
- **D — fixes driven by the emulator view**: moving the VR menu once the stereo test showed it hiding the sculpture is a good example of verification feeding back into usability.
- **B — transparent diagnosis of the delivery blocker**: it quoted the exact 403 and integration errors and offered an inline fallback, then pasted the file as asked, which is exemplary honesty when the environment fails.
- **B — a stubbed DOM/WebGL2 harness that caught a real infinite-recursion bug**: it built creative verification despite having no browser, though it still never proved a real render.
- **H — "✅ Task complete"**: it declares completion when only one fallback-mode screenshot was checked and no XR path was exercised, an overclaim against a device-entry criterion.
- **C — an unexplained "1 failed" tool call**: a failed final verification step goes unmentioned in the summary, which hides information the user would need.
- **G — a shader compile error that only the platform caught, plus "razor-sharp at any magnification"**: the first delivery did not run, and the precision claim is unsupported by any test in the transcript.

## Summary of tests and approach

I read CANDIDATES.md and all eight transcripts in full. I skimmed the very long E and F work logs, but read every visible answer, the tool-call list, and the key tool outputs: test logs, emulator results and error messages. No browser work was needed or done, because the HTML files are not part of this material. For each transcript I logged what was claimed in the final answer and checked it against the visible evidence: tool outputs, screenshots described, and errors shown. I separated measured claims (accuracy statistics, emulator event logs) from narrated ones (an opaque "checks passed"). I checked device-compatibility statements against what each transcript sourced. For example, F's Steam Frame build and E's Steam Frame notes both trace back to web searches in their own logs. I judged each candidate against its own prompt version: A and F against the v0 three.js / three.xr.js requirement, the rest against v1's goal of wow plus usability. Extra user turns and missing replies counted against handoff, but weighed less than verification and honesty. Ties (A vs D, E vs F) were broken by how much of the delivered artifact was actually exercised.
