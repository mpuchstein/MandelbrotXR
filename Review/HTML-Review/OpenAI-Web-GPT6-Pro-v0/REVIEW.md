# HTML Review — candidate-06

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Done-when fulfilment | 8 | Immersive VR, full-size AR and tabletop AR rooms are available through native WebXR. iPhones get a 3D touch, motion and stereo room, which is the best possible without WebXR on iOS. |
| 2. Device/XR compatibility | 8 | Correct feature detection, `local-floor`/`hand-tracking`/`dom-overlay` requested as optional, four input sources (controllers, hands, transient-pointer, screen taps) and a secure-context check. There is no hit-test and no hand meshes. |
| 3. Visual wow effect | 6 | A well-composed gallery with signage, a live minimap wall and a glass case. The fractal itself is a coarse vertex-coloured heightfield (at most 289×217 vertices) with smoothed cliff normals and no env map. |
| 4. Usability & controls | 8 | Excellent 2D UI, guide modal, minimap and presets, plus an in-world 9-button panel, teleport rings and snap turn. The VR panel is low (centre at 0.65 m), there is no hover feedback, and the AR tabletop panel sits in front of the exhibit. |
| 5. Code quality & robustness | 7 | Robust: worker with fallback, generation IDs, transferables, context-loss handling and user activation preserved for `requestSession`. However, the app code ships minified (single-letter identifiers), and palette changes trigger full recomputes. |
| 6. Prompt adherence | 8 | Truly standalone (three r186 embedded, zero network dependencies). three.xr.js is replaced by WebXRManager, with the reason explained in the in-page guide (three.xr.js is archived and uses obsolete APIs). |

**Overall score: 7.5 / 10**

## Scope and method
- The file has 4316 lines and 630 KB, with one inline `<script>` (HTML lines 80–4314). `node --check` passes on the extracted script.
- Everything is bundled and minified. three.js r186, OrbitControls and WebXRManager are vendor code. The application code starts at `function Ic(` (HTML line 4307) and continues through lines 4308–4313.
- Line numbers below are HTML lines plus the minified function name. The pretty-printed app code is about 1,630 lines.
- `grep` finds no external URLs other than a JCGT comment and the XHTML namespace, so nothing is fetched from a CDN.

## 1. Done-when fulfilment — 8
- `Yc()` (L4313) calls `isSessionSupported` for `immersive-vr` and `immersive-ar` through `Promise.allSettled`. Depending on the result it enables "Enter VR", "Enter AR · full-size room" and "Enter AR · tabletop exhibit".
- `Bc()` starts the session. It calls `navigator.xr.requestSession` synchronously, before any `await`, so the transient user activation is kept.
- On the first XR frame, `xd()` places the viewer at (0, eye, 4.8) facing the pedestal by counter-rotating the rig `$t` by the viewer's yaw. This is correct maths for both `local-floor` and `local`; the `local` case falls back to a 1.65 m eye height.
- The room built by `I_()` (L4308) is 14×6×14 m, with walls, ceiling, a grid floor, signage, pillars, a torus "oculus" and a wall screen showing the current window. The Mandelbrot relief stands on a pedestal in the middle. This clearly is "a virtual room with the Mandelbrot set in 3D".
- iPhones have no WebXR, so they cannot enter an immersive session. The page detects this and offers three alternatives: "Walk inside" first-person mode (joystick and drag-look), DeviceOrientation look with iOS `requestPermission` called inside the click, and side-by-side stereo. That is a sensible degradation.
- One deduction: for XR the page needs HTTPS or a browser that treats `file://` as secure. The page explains this honestly; it is a platform constraint, not a code defect.

## 2. Device/XR compatibility — 8
**Sessions**
- VR requests `optionalFeatures: ["local-floor","bounded-floor","hand-tracking"]`.
- AR requests `["local-floor","hand-tracking","dom-overlay"]` with `domOverlay.root = #overlay`.
- Nothing is required, so sessions do not fail on missing features. `bounded-floor` is requested but never used, which is harmless.

**Reference spaces**
- `setReferenceSpaceType("local")` comes before `setSession`.
- A `local-floor` space is then requested and installed with `renderer.xr.setReferenceSpace(s)` (confirmed in vendor code). This works on Quest 3, Pico 4 Ultra, Steam Frame (via `immersive-vr`) and Android Chrome.

**Input**
- `$_()` creates four `getController(i)` objects with rays and hit dots.
- The `select` event raycasts against the visible interactables. The visibility check `K_()` walks up the parent chain.
- This covers tracked controllers, hand-tracking pinch, Vision Pro-style `transient-pointer` and Android `screen` taps. Rays are hidden for the `screen` mode.
- Snap turn (30°) is read from the right-hand `gamepad.axes[2]`.
- `beforexrselect` is suppressed on DOM-overlay buttons, so tapping "Place gallery here" does not also fire a world select. This bug is often missed; here it is handled correctly.

**Gaps**
- No `hit-test` and no `anchors`: tabletop placement is head-relative, and the in-page guide says so honestly.
- No hand models (`XRHandModelFactory` is not used), so hand users see only rays.
- `setFramebufferScaleFactor(Qu ? 0.85 : 1)` keys off `(pointer: coarse)`. On a headset browser that reports coarse pointers this silently lowers the render resolution.

**Fallbacks**
- `isSecureContext` and `navigator.xr` are checked with clear labels.
- WebGL2 is checked up front in `nx()`.
- `devicechange` re-runs detection.

## 3. Visual wow effect — 6
**Strengths**
- A cohesive "observatory" art direction: dark teal palette, serif signage drawn to canvas textures, an engraved formula wall, and an `EdgesGeometry` glass case around the relief.
- A live "THE CURRENT WINDOW" screen mirrors the minimap.
- ACES tone mapping, sRGB output, hemisphere plus two directional lights plus a point light, and fog. The 2D landing UI is polished.

**Fractal fidelity**
- `Ic()` computes a smooth escape count with log normalisation, plus an analytic cardioid and period-2 bulb test. The maths is correct.
- The result is rendered as a **vertex-coloured heightfield**. On the default setting that is 193×145 vertices over 4.2 m, about 2.2 cm per cell.
- The boundary detail is therefore blurry. The cliff from the escaped area up to the flat interior "plateau" becomes stretched triangles, and `computeVertexNormals()` smooths across it, which gives shading smears.
- There is no per-pixel shader fractal on the surface, so zooming (up to 12,800×) never adds detail beyond the mesh grid.

**Lighting**
- No shadows and no environment map. The `metalness: 0.7` trim and pedestal materials will look flat or dark.

Overall it looks tasteful but not spectacular.

## 4. Usability & controls — 8
**2D (desktop and phone)**
- Orbit (damped, clamped) and walk mode with WASD, a joystick and collision against the pedestal.
- Presets (full, seahorse, elephant, satellite), three palettes, a relief-height slider and three detail levels.
- A clickable and keyboard-navigable minimap, zoom ±, stats, a toast system, and a help modal with a focus trap and Escape handling.
- `prefers-reduced-motion` is respected, safe-area insets are used, and there is a mobile bottom sheet.

**XR**
- The in-world panel `D_()` has Destination, Zoom ±, Palette, Relief, Reset, Entrance/Place AR, Detail and Leave XR.
- Four teleport rings are built in `U_()`, and teleporting re-orients the panel toward the user.
- Snap turn only, no smooth locomotion: good for comfort.
- DOM-overlay "Leave XR" and "Place gallery here" buttons are shown in AR.

**Weaknesses**
- The VR panel sits at `Ae.position.set(0,0.65,3.2)`, scaled 0.65, so it spans about 0.19–1.11 m in height. Buttons sit at roughly 0.35–0.78 m, which is low to point at.
- The interactive buttons get no hover or press highlight; only the hit dot shows.
- In tabletop AR the panel is a child of the 0.22-scaled gallery and ends up about 0.55 m in front of the viewer, below eye level. It probably blocks part of the 0.9 m miniature.
- Teleporting is limited to four fixed spots.

## 5. Code quality & robustness — 7
**Good**
- The fractal runs in an inline Blob worker. `F_()` builds it from `Ic.toString()`, which is safe because `Ic` is self-contained.
- Buffers are transferred, and stale results are dropped (`i.id !== Y.generation`).
- Worker errors fall back to the main thread, capped at 128 columns (`od()`).
- Geometry is disposed on rebuild.
- `webglcontextlost` and `webglcontextrestored` are handled.
- XR start failures map `NotAllowedError` and `NotSupportedError` to readable messages (`ud()`).
- Session-end restore in `Vc()` is idempotent, even though it is wired twice: to the session `end` event and to the three `sessionend` event.
- The camera state is snapshotted before XR (`Y_()`) and restored after.
- The XR frame loop is light: one viewer pose and up to four raycasts against about 13 meshes.

**Weak**
- The application code is delivered **minified** (single-letter identifiers, statements joined with commas). As source it is hard to audit or modify.
- Changing the palette (`md()`) recomputes the whole escape-time field although only the colours change.
- The worker queue is never cancelled, so fast zoom clicks on "Fine" queue up redundant computations.
- Small per-frame allocations: `Gc.filter(K_)` runs per controller per frame, and `new D(0,0,1)` is allocated in `W_()`.
- `Bc()` returns silently when `!Y.ready`. This is masked by the loader, so it is minor.
- `zt.xr.setFoveation(1)` is maximum foveation, which visibly blurs the side-wall text on Quest.

## 6. Prompt adherence — 8
- Single file, fully offline, three.js embedded with its MIT licence.
- three.xr.js is not used. The guide's "UNDER THE HOOD" section says three.xr.js is archived and uses obsolete APIs, so it was replaced by the native WebXRManager and a small session/input helper. This is the technically correct choice, and it is disclosed to the user.
- Covers HMDs, AR and phones as asked.

## Bugs found
1. **Minor (usability bug): tabletop AR panel occludes the exhibit.** In `D_()`/`Bc()` (L4312–4313), `Ae` is a child of `ve`. `ve` is scaled to 0.22 and placed 1.25 m ahead (`xd()`), so the panel lands about 0.55 m from the viewer, between the eye and the miniature. It should be re-parented or offset for the `miniature` layout.
2. **Minor: VR control panel is very low.** `Ae.position.set(0,0.65,3.2)` with scale 0.65 puts the buttons at about 0.35–0.78 m height. Teleport clamps the panel height to `0.38–0.8` m (`Sd()`), so it stays low after moving too.
3. **Minor: motion mode is lost after XR.** `Bc()` calls `Zo(!1)`, and `Vc()` restores `mode` but not `motion` (although `Y_()` saves it). A phone user who used Motion before AR returns to touch look.
4. **Minor: render scale depends on pointer type.** `setFramebufferScaleFactor(Qu ? 0.85 : 1)` with `Qu = matchMedia("(pointer: coarse)")` can lower the resolution on headsets whose browser reports a coarse pointer. Phone versus headset is not a pointer property.
5. **Minor: palette change recomputes the fractal.** `md()` → `Bn()` reruns the whole escape-time computation, including on "Fine" (640 iterations) inside VR. Colours could be remapped from cached smooth values instead.
6. **Minor: shading artefacts at cliffs.** `pd()` calls `computeVertexNormals()` on the indexed grid, which smooths normals across the escape cliff and produces smeared shading at the set boundary.

No crash-level or session-breaking bugs were found. User activation, `beforexrselect`, reference spaces and session teardown are all handled correctly.

## Top 5 issues
1. **Major — fractal fidelity is capped by mesh resolution.**
   - Evidence: `Ic()` and `pd()` build a heightfield of at most 289×217 vertices, with colours interpolated per vertex. Zooming to 12,800× never adds detail.
   - Fix: colour (and optionally displace) per fragment in a shader using the same `cx/cy/span` uniforms, keeping the mesh only for coarse relief. Alternatively, add a high-resolution texture of the smooth escape value.
2. **Major (maintainability) — application code shipped minified.**
   - Evidence: L4307–4313 are 20–80 KB lines with single-letter identifiers.
   - Fix: keep the vendor bundle minified, but inline the app code un-minified in a separate `<script>` block.
3. **Minor — XR panel ergonomics.**
   - Evidence: the panel height is 0.65 m (`D_()`, `Sd()`), and in tabletop AR it occludes the exhibit.
   - Fix: place it at about 1.0–1.2 m (or relative to eye height), tilt it toward the user, and for `miniature` give it its own world position beside the table. Add hover highlights through the per-frame raycast in `j_()`.
4. **Minor — AR placement is head-relative only.**
   - Evidence: no `hit-test` or `anchors` in `optionalFeatures`.
   - Fix: request `hit-test` as optional and, when granted, snap the tabletop exhibit to a detected plane, keeping the current fallback.
5. **Minor — rendering polish and resource use.**
   - Evidence: no env map, so metallic parts look dull. `setFoveation(1)` blurs peripheral text. A palette change triggers a full recompute.
   - Fix: add a `PMREMGenerator` + `RoomEnvironment` env map (already part of three), use foveation of about 0.5, and cache smooth values so colours are remapped without recomputing.

## Strengths
1. Correct and careful WebXR plumbing: synchronous `requestSession`, optional features only, `local-floor` with a `local` fallback, `beforexrselect` suppression, rig re-centring, and clean state restore on exit.
2. Broad input coverage: controllers, hands, transient-pointer and screen taps, with teleport, snap turn and a full in-world control panel.
3. Thoughtful non-XR fallbacks for iOS: walk mode with a joystick, DeviceOrientation with `requestPermission`, and split-screen stereo, plus clear secure-context and support messaging.
4. Truly standalone and offline: three r186 embedded, a worker built from a Blob, no CDN, a WebGL2 pre-check and context-loss recovery.
5. Polished UX and accessibility on the 2D side: guide modal with focus trap, keyboard-navigable minimap, reduced-motion support, safe-area insets and a responsive layout.

## Verdict
A robust, well-engineered submission. Its WebXR session and input handling is better than typical, and it degrades gracefully on iPhones, so a headset or Android user can reliably enter a furnished room with a 3D Mandelbrot relief. The main weakness is the visual centrepiece: a mid-resolution vertex-coloured heightfield that gains no detail when zooming. The app code also ships minified, which hurts maintainability.
