# HTML Review — candidate-07

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Done-when fulfilment | 9 | immersive-vr and immersive-ar, plus gyro "magic window" and Cardboard stereo fallbacks, all put the user in a room with a GPU-computed Mandelbrot heightfield |
| 2. Device/XR compatibility | 8 | Feature-detected VR/AR buttons, local-floor→local fallback, hands/controllers/screen taps, iOS motion permission, a projection-layer workaround; iPhone gets non-WebXR modes only (a platform limit) |
| 3. Visual wow effect | 8 | Deep zoom by perturbation to 1e-12, three height "shapes", five palettes, colour flow, a 3× context wall screen, a gallery room with glow strips; no shadows, and the vertex grid is coarser than the field |
| 4. Usability & controls | 8 | Clear intro sheet with capability notes, an in-world panel, control signs on the walls, HUD, keys, tour; toasts are invisible in VR and tour stops end up off-centre |
| 5. Code quality & robustness | 8 | Well-sectioned 1.8k-line IIFE, budgeted strip compute, triple-buffered fields, async readback, error paths; one global prototype monkey-patch, frequent panel re-uploads, a debug handle left in |
| 6. Prompt adherence | 9 | Single standalone file with three.js r186 inlined (tree-shaken), using three's built-in WebXRManager (there is no real "three.xr.js"); 3D room plus fractal as asked |

Line numbers below refer to `index.html`. The application script starts at line 4475, and lines 243–4473 are the bundled three.js build.

## Criterion notes

**1. Done-when (9).** `detectSupport()` (≈6111) shows only the buttons that work. `enterXR()` (≈5718) starts `immersive-vr` or `immersive-ar` and sets up the rig, reference space and overlay. Non-XR phones get `enterLook()` (≈5928): gyro "Look around" or a side-by-side "Phone headset" mode (stereo render at ≈6212). The fractal is a displaced 1.6 m heightfield on a plinth (`TERRAIN_VS`, ≈4732) inside a 10×10×4.2 m room (`buildRoom`, ≈5255). Every target device reaches a 3D Mandelbrot room. On iPhone that has to be the non-WebXR modes, and the page explains why (≈6120).

**2. Compatibility (8).**
- Optional features: `local-floor`, `bounded-floor`, `hand-tracking`, `layers`, plus `dom-overlay` for AR (≈5720–5722).
- It probes `local-floor` and falls back to `local` with a guessed eye height (≈5737–5743).
- It works around three r186 creating projection layers whenever `XRWebGLBinding` exists. I confirmed in the bundled code that three checks only `"createProjectionLayer" in XRWebGLBinding.prototype`, so the workaround is real. It deletes the prototype method when `layers` was not granted (≈5731–5736).
- Input: `select` uses `frame.getPose(targetRaySpace)`, so tracked-pointer, hand pinch, AR screen taps and transient-pointer (gaze-and-pinch) all work (`onXRSelect`, ≈5777). `squeeze` zooms out. There is haptics, a joint-sphere hand model (`updateHand`, ≈5698), smooth locomotion on the left stick and 30° snap turn on the right.
- iOS: `DeviceOrientationEvent.requestPermission()` is called inside the tap handler (≈5917). There are secure-context and missing-WebXR notices.
- Quest 3 gets both VR and passthrough AR, with the room hidden in AR and a "Show room" toggle.
- Missing: AR has no hit-test or anchors (the plinth is placed 1.6 m ahead). Vision Pro and other unknown headsets fall into `IS_MOBILE` or desktop quality guesses based on the user-agent string (≈4500).

**3. Visuals (8).**
- `COMPUTE_FS` (≈4591) builds a float64 CPU reference orbit, then runs float32 GPU perturbation with rebasing. It computes smooth iteration counts and a distance estimate, packs both as 16-bit values, and analytically skips the cardioid and bulb.
- Terrain shading (≈4761): per-pixel normals from the field, Blinn specular, a glossy fresnel "obsidian" interior, an edge glow near the boundary, ACES tone mapping. There are three shapes (Plateau, Crater, Distance), five palettes and colour cycling.
- The room: terrazzo canvas floor, light slots, a ceiling ring, a metal-rimmed plinth, PMREM room environment, spot, fill and hemisphere lights, and a wall screen showing 3× the plinth's width with a frame marking the plinth region.
- Weaknesses: no shadows or AO. Heights come from a 320² vertex grid sampling a 1024² field, so geometric detail is limited and can shimmer while zooming.

**4. Usability (8).**
- Good onboarding: a "How to use it" details block, VR/AR as the primary button when supported, and control instructions painted on the room's side wall.
- The in-world canvas panel (`drawPanel`, ≈5448) shows the centre coordinate, width, iteration count, a progress bar and 13 actions. Back history, a guided tour, recenter, and adjustable height and detail are all there.
- Comfort: zooming animates the content, not the viewer. Snap turn is good, but locomotion is smooth only, with no vignette or teleport.
- Gaps: `toast()` is DOM-only, so headset users never see "precision limit" or "Nothing to go back to". Tour stops are not centred (see bugs).

**5. Code quality (8).**
- Clear sections and good comments.
- Work is cut into scissored strips under an adaptive per-frame budget (≈6167, `runCompute` ≈4994). The render target is correctly saved and restored, and `xr.enabled` is toggled while computing.
- Render-target pools avoid reallocations (`freeRT`, `finishJob` ≈5031). Old fields cross-fade as fallbacks.
- Picking uses non-blocking `readRenderTargetPixelsAsync` (≈5042), and the terrain hit is found by ray-marching plus bisection.
- Context loss and WebGL2 absence produce a fatal message. `node --check` passes on both scripts.
- Downsides: the global `delete XRWebGLBinding.prototype.createProjectionLayer`, panel canvas re-uploads, and `window.__mandelbrotRoom` debug/automation hooks left in production (≈6236).

**6. Adherence (9).** Fully standalone: no CDN or network dependency, 668 KB. three.js is embedded, and WebXR goes through `renderer.xr`. It writes its own buttons and controller visuals instead of using the VRButton and XRControllerModelFactory addons. That is justified: it needs custom UI, and the addons would require extra inlined code.

## Bugs found

1. **Tour targets end up near the view edge, not centred.** `zoomAbout()` (≈5105) keeps point *p* at a fixed relative offset `(p − c)/span` all the way down. `updateTour` (≈5121) always restarts from HOME (−0.6, 0, span 3.2), so each stop keeps its HOME-relative offset:
   - Minibrot at −1.755: about −0.36 span, ending at u≈0.14.
   - Elephant valley: about +0.28, ending at u≈0.78.
   - Three-way branch: v≈0.80.
   - Seahorse is the only stop that ends near the centre.
2. **Toasts are invisible in immersive VR** (`toast()`, ≈4538). Messages from `zoomInto` (precision limit, ≈5101), `back`, tour start and stop names, and so on never reach the headset user.
3. **Haptic "success" pulse fires even when the zoom is refused.** `performSelect` returns `true` after calling `zoomInto` even when it bailed out at `MIN_SPAN` (≈5623 and ≈5797).
4. **The global prototype mutation is permanent.** After one session without `layers` (e.g. AR on Android), every later session in that page load, including Quest VR sessions that grant `layers`, falls back to `XRWebGLLayer` (≈5735).
5. **Panel texture re-upload in the XR frame loop.** `runCompute` sets `uiDirty = true` on every frame with pending work (≈5028), so the 1024×826 canvas is redrawn and re-uploaded about 8×/s while anything renders (≈6204). That is a measurable cost on standalone headsets.
6. **The pick heightfield does not match the rendered geometry.** Rays march against the 256² *preview* field (`readPickField` triggers only for `kind === 'prev'`, ≈5037), while the mesh displays the 1024² full field. On tall settings the cursor can float above, or sink into, thin spires.
7. **`#status` captures pointer events.** It inherits `pointer-events: auto` from `#overlay > *` (CSS line 51), so taps on the top-centre strip of the canvas do nothing in HUD or AR mode.
8. **Minor:**
   - Exiting Phone headset mode leaves the screen orientation locked to landscape (`enterOrbit`, ≈5952).
   - The keyboard shortcuts `h`/`H`/`f`/`r` are not listed in the help text.
   - `bounded-floor` is requested but never used.

## Overall score: **8 / 10**

## Top 5 issues

1. **Major — tour stops off-centre.** `zoomAbout` + `updateTour` (≈5105, ≈5121). Fix: in the tour, interpolate the centre toward the stop (e.g. `setTarget({cx: stop.cx, cy: stop.cy, span: target.span*factor})`) instead of zooming about a fixed point, or pan to the stop at HOME span first.
2. **Major — no in-headset feedback channel.** `toast()` (≈4538). Fix: mirror toasts onto the 3D panel's status line (it already has `st.extra`) or onto a small head-locked text sprite while `renderer.xr.isPresenting`.
3. **Minor — global `XRWebGLBinding.prototype` deletion** (≈5731–5736). Fix: save and restore the descriptor in `onXREnd`, or set the check per session (e.g. temporarily shadow it with `Object.defineProperty` and restore it after `setSession`).
4. **Minor — panel canvas re-uploaded during every compute pass** (≈5028, ≈6204). Fix: mark dirty only when the progress percentage changes by at least 5 %, or draw the progress bar as a separate small mesh or uniform.
5. **Minor — geometric resolution and pick mismatch** (grid preset ≈4503, `readPickField` ≈5037). Fix: raise the grid on desktop or use LOD, and read back the full field (or a downsampled max) for picking, so the hit point matches the displayed surface.

## Strengths

1. A real deep-zoom engine: CPU float64 reference orbit plus GPU float32 perturbation with rebasing, distance estimation, and analytic interior skipping, with a built-in CPU cross-check (`compareWithCPU`).
2. XR-safe progressive compute: scissored strips under an adaptive frame-time budget, preview then full passes, and cross-fades between buffered fields. The headset frame loop never stalls.
3. The broadest device coverage possible from one file: VR, passthrough AR with DOM overlay, gyro magic window, Cardboard stereo and desktop orbit, each feature-detected with honest notices about HTTPS and WebXR.
4. Thoughtful in-world UX: a reachable canvas control panel with hover states, a context wall screen with a frame marking the plinth region, instruction signs, snap turn, recenter, haptics and a hand-joint visualisation.
5. Clean, well-commented structure and defensive error handling: WebGL2 check, context loss, session-start failures, reference-space fallback, and a projection-layer issue in this three.js build that the author identified and worked around.

## Verdict

This is a very strong, carefully engineered submission. A user on Quest, Pico, a similar headset, Android or iPhone lands in a well-designed room with a genuinely deep-zoomable 3D Mandelbrot landscape, and the compute pipeline is built to respect XR frame budgets. The remaining issues are polish, not blockers: off-centre tour stops, missing in-headset messages, and a hacky global layers workaround.
