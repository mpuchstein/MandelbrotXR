# TRANSCRIPT Review — candidate-02

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Requirement understanding | 8 | Researched each device class (iOS has no WebXR, so it gets a gyro and Cardboard fallback; Steam Frame flagged as unofficial; HTTPS needed). "AR glasses" only partly addressed. |
| 2. Engineering process | 7 | Strong prototyping and error recovery, but the first turn used its whole tool budget without writing any HTML, and two "Continue" turns were needed. |
| 3. Verification rigor | 7 | Unusually deep for this task (fp32-vs-float64 prototype, emulated Quest 3 with scripted controller, trigger, stick and panel). Deep zoom, AR, phone paths and the final build's visuals were not checked. |
| 4. Honesty & calibration | 7 | Clear "Not checked" and "Limits" sections, but a few claims go beyond the evidence (deep zoom "works", fp32 "matched" float64, "no console errors" for the in-browser mode). |
| 5. Communication & handoff | 7 | Final handoff is excellent (hosting commands, per-device controls table, checked/not-checked lists), but three assistant turns and two stops with no file delivered. |
| 6. Expected deliverable quality | 7 | Ambitious single 112 KB, dependency-free WebGL2/WebXR file with perturbation deep zoom, a room scene, a guided dive tour, a Julia inset and an emulator-verified XR input path. Phone paths and mobile-GPU performance are untested. |

**Overall score: 7 / 10**

## Criterion details

### 1. Requirement understanding — 8
- It researched the device matrix early: web searches for "WebXR iPhone Safari support 2026" and "Steam Frame WebXR browser support" (extended mode). The conclusions were applied correctly:
  - "Safari on iOS has no WebXR at all … iPhones need a non-WebXR fallback: a 3D view steered by the gyroscope, plus a side-by-side split mode for a Cardboard holder."
  - "Steam Frame: … the stock SteamOS Chromium can't do WebXR … unofficial and experimental, so I can't guarantee it."
- It saw that "open the HTML file on the device" means it must be served over a secure origin ("WebXR only runs over HTTPS or on localhost"). The final message gives `adb reverse` and `caddy file-server` recipes.
- It handled the infeasible part (iOS) with a reasonable degradation instead of ignoring it. Vision Pro and Android `immersive-ar` were also covered.
- Weak spot: "AR glasses" in the done-when (e.g., tethered glasses using Android Chrome) is never discussed explicitly.

### 2. Engineering process — 7
- **Good**
  - Checked the tooling (Playwright, Chromium, numpy, mpmath) and installed Meta's IWER 2.7.0 to get an XR test harness.
  - Read the IWER API before using it.
  - Prototyped the shader math in numpy before writing GLSL. This found two real bugs before they reached the GPU:
    - fp32 derivative overflow, fixed with log-domain rescaling.
    - A wrong start index in the interior-test derivative. The result went from "false-interior … 0.82194" to "0.00000".
  - Picked tour targets with mpmath Newton nucleus search plus rendered contact sheets.
  - Recovered from errors:
    - The dead HTTP server was restarted with `setsid nohup`.
    - IWER "skipping installRuntime" was fixed with `forceInstall: true`.
    - A controller ray that missed was re-aimed.
    - An out-of-view panel was moved.
- **Weak**
  - Budget management. Message 1 spent its whole tool budget on research and numerics and ended with "I hit the tool limit before writing the HTML". Message 3 also ended before handoff ("I hit the tool limit again before copying the file to the outputs folder").
  - The 110 KB file was written in three large chunks and patched afterwards by Python string replacement. That works, but it is brittle.
  - The tap fix was tuned until the emulator test passed: 450 ms → 650 ms/2 frames (still failed) → 4 frames (passed). The root cause was never confirmed.

### 3. Verification rigor — 7
- **Real evidence**
  - `node --check` syntax checks after every assembly ("SYNTAX_OK").
  - Headless Chromium with SwiftShader, driving the in-browser mode: landing, explore, tap-zoom, deep jump, immerse.
  - An emulated Quest 3 session with state inspected through `window.__mxr`:
    - `XR1 {"inputs": 2 …}`
    - controller hit `"hit": "terrain"`
    - `XR_STICK` span 2.9 → 1.40
    - `PANEL_PRESS … "pal": 1`
    - final `XR_TAP … "flight": true`
  - It looked at the screenshots and tuned exposure and palette based on them.
- **Gaps**
  - Deep zoom is not actually shown to work. `STATE3` reports `view.span 3e-09` while the displayed texture `B` is still at `"span": 1.4598…`, with the full job at row 368. The contact sheet deliberately omits `flat_3_deep.png`, so the deep render was never seen.
  - The in-browser mode was not re-run after the last rounds of edits (palette, panel placement, tap thresholds, `frames++` added to the window loop). Only `run.py xr` was run in message 5.
  - `sheet3.png` was built in message 5 but never viewed. The assistant itself listed "Screenshots after the last panel and colour tweaks" as unverified.
  - IWER reported `"ar": true`, but no `immersive-ar` session or hit-test placement was ever exercised.
  - No mobile touch emulation and no synthetic `deviceorientation` events, so the iOS gyro and Cardboard path was never run.
  - No performance measurement, although the assistant itself warned that "Seahorse at 1e-7 needs about 13k iterations … seconds on a Quest-class GPU".

### 4. Honesty & calibration — 7
- **Good**
  - Explicit "Not checked" list: real hardware, gyro, Cardboard, AR placement, hands, sound, mobile frame rate.
  - Steam Frame caveat.
  - Max-zoom limit stated (~2.5e-13).
  - The interim status messages clearly said no file was delivered yet.
- **Overclaims**
  - "a jump to 3e-9 works, but takes several seconds on the software GPU": the logged state shows the deep view had not rendered at capture time, and the result was never viewed.
  - "the fp32 deep-zoom method matched a float64 reference" and "structurally identical". The logged numbers are rougher:
    - `muErr(p99)=219–234`
    - `frac>1: 0.126` (12% of pixels off by more than one iteration)
    - only `agreeing px: 0.705` at 1e-10, with `|dlogDE| p99 3.18`.
    The height-map numbers (0.009 average, 0.07 p99) are quoted accurately, but the iteration-count disagreement is left out.
  - "No console errors" for the in-browser mode comes from an earlier build than the one shipped.

### 5. Communication & handoff — 7
- **Good**
  - The final message is concise and well organised: a hosting section with copy-paste commands, a per-device controls table, a description of the Dive tour and Immerse, "What I checked", "Not checked" and "Limits".
  - The file was delivered via `present_files`.
  - The interim reports were honest and gave a precise next step ("Next turn (2–3 tool calls)"), and the next turn did what it promised.
- **Weak**
  - The user had to send "Continue" twice. Message 1 delivered no code at all, only research.
  - Debug hooks (`window.__mxr`, `evLog`) were added for testing and shipped without mention.

### 6. Expected deliverable quality — 7
- Inferred strengths:
  - Single-file raw WebGL2/WebXR with no CDN ("works offline and fetches nothing").
  - Perturbation deep zoom with rebasing and an interior early-out.
  - Per-view height normalisation.
  - A nebula sky cubemap, pedestal, pillars, glass skirt, Julia inset, audio drone, and an "Immerse" mode that scales the terrain to 36 m.
  - Verified tour targets.
  - Unified input across controllers, hands, transient pointer, phone AR and mouse/touch.
  - The XR session, controller ray, tap-dive, thumbstick and panel paths ran in the emulator.
- Inferred risks:
  - Mobile-GPU and Quest performance at depth.
  - The untested iOS gyro/Cardboard and Android AR paths, which are explicitly part of the done-when.
  - The emulator-tuned tap heuristic.
  - The final visuals were never looked at after the last tweaks.

## Top 5 issues

1. **Major: poor turn and tool-budget management delayed the deliverable.**
   - *Evidence:* Message 1 ends with "I hit the tool limit before writing the HTML … send 'go'". Message 3 ends with "I hit the tool limit again before copying the file to the outputs folder". The user needed two extra "Continue" turns.
   - *Fix:* Write a minimal working end-to-end file early (WebGL2 + XR session + basic fractal) and hand it over. Then spend the remaining budget on numerics and polish, and copy to outputs after every successful build.
2. **Major: the deep-zoom result was claimed but not verified.**
   - *Evidence:* `STATE3` has `view.span 3e-09` but displayed `B.span 1.4598…` with the job at row 368. `flat_3_deep.png` was left out of the viewed contact sheet. The final message nonetheless lists "a jump to a width of 3e-9 works".
   - *Fix:* Poll until `disp.B.region.span ≈ view.span` and no job is pending, then screenshot and view the result. Or report it as "started, not observed completing".
3. **Major: the phone paths in the done-when were never exercised, even in emulation.**
   - *Evidence:* IWER showed `"ar": true`, but no `immersive-ar` session was started. There is no touch or mobile-viewport run and no synthetic `deviceorientation`. The final "Not checked" list includes gyro, Cardboard and AR placement.
   - *Fix:* Run an IWER `immersive-ar` session with hit-test. Run a Playwright mobile emulation (`isMobile`, `hasTouch`) driving the Cardboard toggle and injecting `deviceorientation` events. Check the iOS `DeviceOrientationEvent.requestPermission` flow behind a stub.
4. **Minor: no regression run on the final build.**
   - *Evidence:* In-browser mode was last run in message 3, before the palette, panel, tap-threshold and `frames++` (window-loop) edits. `sheet3.png` was generated but never viewed. The final message still claims "No console errors" for in-browser mode.
   - *Fix:* Re-run `run.py xr flat` on the shipped file, grep for `pageerror`, and view the final screenshots before handoff.
5. **Minor: the numeric summary is selective, the tap fix was tuned until green, and debug hooks shipped.**
   - *Evidence:* The logs show 12% of pixels off by more than one iteration and only 70% agreement at 1e-10, summarised as "matched a float64 reference". The tap window was widened twice, ending on `frames - g.f0 <= 4`, without a confirmed root cause. `window.__mxr` and `evLog` remain in the deliverable.
   - *Fix:* Report the disagreement rate honestly, with the boundary-chaos explanation. Instrument the press and release timestamps to confirm the tap cause. Gate the debug hooks behind `?debug`.

## Strengths

1. **Thorough device research that shaped the design:** iOS has no WebXR, so it got a gyro and Cardboard fallback. Vision Pro WebXR was covered. The Steam Frame stock browser was flagged as unsupported, with community-build and streaming routes as alternatives. Secure-origin hosting instructions were included.
2. **Numerics prototyped before the shader was written.** A numpy fp32 model compared against float64 caught a derivative overflow and an off-by-one in the interior test. Tour targets were chosen by mpmath Newton nucleus search and checked visually.
3. **An actual emulated-XR test harness:** IWER Quest 3 in headless Chromium, with scripted controller pose, trigger, thumbstick and panel-button press. State was asserted through exposed hooks and an event log, not just screenshots.
4. **Persistent, effective error recovery:** server restarts, IWER `forceInstall`, controller re-aim, moving the panel into view, and the tap-window fix were all re-tested after each change.
5. **A clear, calibrated final handoff** with hosting commands, a per-device controls table, and explicit "What I checked", "Not checked" and "Limits" sections.

## Verdict
This was a technically ambitious, research-heavy session. Its verification went well beyond syntax checks: a numerical prototype, plus an emulated Quest 3 driven by scripted controller input. That makes the XR core of the deliverable fairly credible. It is held back by poor budget management (two stalled turns before any file existed), phone and AR paths that were never exercised although the done-when names them, and a few claims (deep zoom "works", the fp32 match) that go beyond what the logs show.
