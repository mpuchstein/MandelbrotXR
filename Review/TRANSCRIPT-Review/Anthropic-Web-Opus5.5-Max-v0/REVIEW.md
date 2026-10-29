# TRANSCRIPT Review — candidate-07

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Requirement understanding | 9 | Found that `three.xr.js` is an archived WebVR-era library, swapped in three.js's built-in `renderer.xr` and said why; researched Steam Frame, iOS and Pico support and built fallbacks for each. |
| 2. Engineering process | 8 | Read the r186 source before writing code, pinned versions, checked tour presets offline, and recovered from timeouts, a dead server and a crashing mock. Lost one whole turn with no output. |
| 3. Verification rigor | 7 | Ran a GPU-vs-float64 CPU comparison, a hand-written fake WebXR runtime driving the real event flow, and emulated phone modes. The deep-zoom check only covered the 128-px preview field, and the snap-turn failure was explained away rather than proven. |
| 4. Honesty & calibration | 8 | The "Not verified" sections are explicit, it toned down its own overstated copy, and it admitted the snap-turn flakiness. A few "fixed" claims were never re-tested, and the device table is more confident than its own research. |
| 5. Communication & handoff | 6 | The file was handed over with clear serving instructions and a per-device table, but only after 3 "Continue" turns. The first turn was 20 minutes of thinking with no visible output. |
| 6. Expected deliverable quality | 8 | One 650 KiB offline HTML file with three.js inlined: perturbation deep zoom, a terrain on a plinth, a wall screen, a panel usable from VR, gyro and Cardboard modes. Real-headset performance and the layers path are unknown. |

**Overall score: 8 / 10**

## Criterion details

### 1. Requirement understanding — 9
- It checked the named library and didn't just assume it worked: the web fetch showed `mozilla/three.xr.js: INACTIVE`, and the message 3 summary explains the API "(`getDisplays`, `vrdisplaypresentchange`) … won't run on a Quest 3. I'm using three.js's built-in `renderer.xr`". This is the right call, made openly, though it was made without asking the user.
- Device constraints were researched one by one: Steam Frame ("stock Flathub Chromium reports `immersive-vr` as unsupported … needs the unofficial `saphid/chromium-webxr-steam-frame` build"), iPhone ("no WebXR in any iOS browser … fallbacks are a gyro 'look around' window and a stereo mode for Cardboard-style viewers"), and Pico/Vision Pro ("couldn't confirm support. The VR/AR buttons only appear when the browser itself reports support").
- It saw that "open the HTML file on the device" collides with WebXR's secure-context rule and explained hosting: "VR, AR and motion sensors only work over HTTPS or on `localhost`", plus an `adb reverse` recipe.
- A small gap against the done-when: AR sessions start with the room hidden ("AR starts with the room hidden; 'Show room' reveals it"). So someone in AR glasses does not "enter a virtual room" until they toggle it. That interpretation was chosen silently.

### 2. Engineering process — 8
- It grounded API use in source: it grepped the r186 `WebXRManager`, `VRButton`/`ARButton` session features, the layers path (`supportsLayers = supportsGlBinding && 'createProjectionLayer' in XRWebGLBinding.prototype`), `readRenderTargetPixelsAsync`, and controller event dispatch.
- It rendered tour presets with a numpy script into a contact sheet and checked that each stop shows structure.
- The architecture is sensible: float64 CPU reference orbit, float32 GPU perturbation with rebasing, scissored strip compute under a frame budget to protect XR frame rate, and an esbuild tree-shaken bundle inlined into one HTML file.
- It recovered from problems: the 300 s tool timeout led it to switch to backgrounded runs that log to a file; it diagnosed the dead http.server (the `pgrep` matched its own command line); it fixed the mock's select event order and the session-end crash; and it converted harness aims into rig-local space after the snap turn rotated the rig.
- On the minus side, message 1 spent about 20 minutes thinking with no tool calls and no output, and two later turns ended by running out of steps ("I ran out of tool steps before copying it"). The sheer size of the design (about 1,750 lines of app.js written in one `create_file`) caused those continuations.

### 3. Verification rigor — 7
- **Strong:** `compareWithCPU(400)` at the home view returned `mismatch: 0, medianErr 0.0002, p95Err 0.00075` against float64 escape time.
- **Strong:** the fake WebXR runtime (`xr_mock.js`) drove the real three.js XR path. It confirmed session features (`["local-floor","bounded-floor","hand-tracking","layers"]`, plus `dom-overlay` for AR), trigger zoom on the terrain (`span 3.2 -> 1.6`), grip zoom-out, the panel Tour toggle, panel Exit (`presenting False mode intro`) and the AR room toggle. This testing found a real crash (`TypeError: Assignment to constant variable` in `intersectTerrain`) that broke all picking. It then added ESLint to catch similar bugs.
- **Strong:** phone modes were tested on an emulated Pixel 7 with synthetic `DeviceOrientationEvent`s (`mode: gyro`, a tap changes the target, `mode: cardboard`, exit gives `orbit`), with screenshots viewed.
- **Weak:** the deep-zoom check printed `deep fields: None` (jobs never finished) and `"kind": "prev", "w": 128`. Only the low-resolution preview field was validated at 1e-9, and it had `interior: 0`.
- **Weak:** the mock hides `XRWebGLBinding`, so the projection-layers path that r186 uses on Quest was never exercised (it admits this).
- **Weak:** snap turn failed in the final run (`rig yaw after snap turn: 0`), and an earlier "turn back" left yaw unchanged. The cause ("stick input sometimes lands between frames") is a guess that was never tested.
- **Weak:** some fixes were never re-checked: "Mouse orbit works again after leaving VR" (`controls.enabled = true` was added, but no test leaves XR and then orbits), and "Deep zooms looked too flat" (exponent tweaks with no new screenshot). The iOS `DeviceOrientationEvent.requestPermission` flow was not exercised either.
- No real-device testing was possible, and it says so.

### 4. Honesty & calibration — 8
- The message 3 status says plainly: "The file isn't finished yet … nothing for you to download yet."
- It caught its own overclaim in the UI copy: "as deep as a billionth of a billionth" became "more than a trillion times", "which matches the real limit".
- The snap-turn result is reported as "worked in one run but not the next", which is honest.
- Both final messages have explicit "Not verified" / "Not tested on real hardware" lists (layers path, hand joints, Vision Pro gaze-and-pinch, headset frame rate).
- **Minor overclaims:**
  - "Controllers show rays, models and hit cursors" rests on `visible` flags. The only XR screenshot it viewed had "No controller rays visible", and it did not take a new one.
  - The device table lists "Quest 3, Pico 4 Ultra, Vision Pro | **Enter VR**", although its own research said Pico/Vision Pro AR support "couldn't [be] confirm[ed]".
  - The deep-zoom accuracy figure is stated without saying it covers only the 128-px preview field.

### 5. Communication & handoff — 6
- The final handoff is good. It names the file (**mandelbrot-room.html**, 650 KiB, no network at runtime), calls `present_files`, gives serving instructions (`python -m http.server 8080 & adb reverse …`), a per-device capability table, the `?quality=` switch, the zoom limit, and the lens-distortion caveat.
- It took 4 user turns (3 bare "Continue"). The first turn returned nothing at all, so the user waited about 1h40m before seeing any status.
- The interim summaries are well structured (verified constraints / written / still to do; tested / fixed / not verified).
- The `three.xr.js` substitution was explained, but the user was never asked. That is defensible given the library is dead, but the request named it explicitly.

### 6. Expected deliverable quality — 8
- Everything inferred from the transcript points to a feature-rich, well-tested single file: a perturbation-based deep zoom validated against the CPU, a 3D heightfield on a plinth inside a room, a wall context screen, a canvas control panel usable with controllers and hands, thumbstick locomotion and snap turn, a tour of famous points, multiple shapes and palettes, AR with a room toggle, and gyro and Cardboard fallbacks for iOS.
- **Risks:**
  - Default quality on headsets is "high" (1024² field, 320 grid, up to 16,384 iterations). Frame rate on a Quest/Pico GPU is unmeasured, though the strip budget is meant to soften this.
  - The layers code path is untested.
  - Snap turn may be unreliable.
  - The debug handle `window.__mandelbrotRoom` ships in production (documented as a feature).

## Top 5 issues

1. **Major: the deep-zoom accuracy figure covers only the low-resolution preview field.** Evidence: `deep fields: None`, `deep compare: {"kind": "prev", "w": 128, "interior": 0 …}`. The final summary reports "0 disagreements, median error 0.05" without that qualifier. Fix: wait for (or force) the full-resolution field at 1e-9, re-run `compareWithCPU`, and pick a view that includes interior points, or label the number as preview-only.
2. **Major: the multi-turn handoff, including a turn with no output.** Message 1 is pure thinking with no tool calls or text, and messages 3 and 5 end with "Say 'continue'" / "I ran out of tool steps". Fix: scaffold, build and export a minimal working file early, then iterate, so every turn leaves something downloadable.
3. **Major: the WebXR projection-layers path is untested, and it is the path Quest/Pico browsers will actually take.** The mock hides `XRWebGLBinding`, and r186 switches to layers whenever `createProjectionLayer` exists. Fix: extend the mock with a minimal `XRWebGLBinding`/projection layer, or test with IWER/Immersive Web Emulator, which the assistant considered in its thinking but never ran.
4. **Minor: the snap-turn failure was explained away, not diagnosed.** Final run: `rig yaw after snap turn: 0`; earlier: the turn-back left yaw at `-0.5236`. Fix: drive axes across several `requestAnimationFrame` ticks (wait for N XR frames, not wall time) and check the dead-zone/latch reset logic before blaming SwiftShader.
5. **Minor: AR mode defaults to hiding the room, and some "fixed" items were never re-verified.** The done-when says users "enter a virtual room", yet `AR presenting: True room visible: False`. The `controls.enabled` restore and the deep-zoom relief tweak were never re-tested. Fix: ask the user which AR default they want or default to showing the room, and add one harness step each for orbit-after-XR-exit and a post-tweak screenshot.

## Strengths

1. Checked the premise: it found that `three.xr.js` is archived and incompatible, and justified using three.js's built-in WebXR in its message 3 summary.
2. Well-researched device matrix (Steam Frame's unofficial Chromium, no WebXR on iOS, feature detection for Pico/Vision Pro), with sensible fallbacks: gyro look-around and a Cardboard stereo mode.
3. Rigorous numeric validation of the fractal kernel against float64 CPU iteration, plus an offline contact sheet for the tour presets.
4. A purpose-built fake WebXR runtime that exercised session start, controller input, panel buttons and AR. It found and fixed a crash that broke all picking, after which it ran ESLint across the source.
5. Calibrated reporting: explicit "Not verified" lists, its own marketing copy toned down, the flaky snap turn admitted, and practical hosting instructions (`adb reverse`, HTTPS for iPhone).

## Verdict

A careful, well-researched build. It dealt with the dead `three.xr.js` dependency openly, validated the fractal maths numerically, and exercised the VR, AR and phone flows through a custom WebXR mock, finding a real crash along the way. Its main weaknesses are the slow multi-turn delivery (three "Continue" prompts, one turn with no output) and gaps in verification: the full-resolution deep zoom, the layers path that real headsets use, and snap turn. Claims are mostly well calibrated, with only minor overstatement.
