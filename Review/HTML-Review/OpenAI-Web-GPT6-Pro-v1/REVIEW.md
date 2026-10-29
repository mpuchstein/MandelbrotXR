# HTML Review — candidate-01

| Criterion | Score | Reason |
|---|---|---|
| 1. Done-when fulfilment | 8 | Quest/Pico/PCVR enter an `immersive-vr` room with a 3D escape-time relief. Android gets `immersive-ar` (a 6DoF window into the room). iPhone gets a non-immersive touch/gyro 3D view, the best available without WebXR on iOS. |
| 2. Device/XR compatibility | 8 | VR+AR, `local-floor`→`local` fallback, hand-tracking, transient-pointer, gaze-dwell, snap turn, teleport, secure-context and iOS motion-permission handling. AR is opaque and dom-overlay is dead code. |
| 3. Visual wow effect | 7 | Custom contour/rim/spec terrain shader, noise nebula sky, star and spark particles, glowing rings, canvas signage. No env map (dull metals), no bloom, a 2.5D heightfield, and low resolution in XR. |
| 4. Usability & controls | 7 | Polished 2D UI, presets, help/XR dialogs, a 9-button in-world panel with grip-summon. In XR you can only zoom at the centre, and the set's plateau sits above eye height. |
| 5. Code quality & robustness | 7 | Worker + main-thread fallback, cancellation tokens, adaptive quality, error mapping, disposal. But the app code ships minified, with about 120 un-instanced room draw calls and some dead paths. |
| 6. Prompt adherence | 9 | One self-contained 656 KB file with three.js r186 embedded, zero network requests, WebXR as asked. |

**Overall score: 7.5 / 10**

> Note on citations: the whole `<script>` (three.js plus the app) is minified onto a few very long lines. Locations below give the **file line** plus the minified function or identifier. The app code covers lines 4359 (tail) to 4503: presets `gs`, quality table `Hh` and compute `Gh` at 4359; fractal exhibit `Wh` at 4462; room `Xh` at 4493; XR controller `qh` and bootstrap `r0` at 4503. The script passes `node --check`. Every `getElementById` target exists in the markup.

## 1. Done-when fulfilment — 8
- `r0` (4503) creates a WebGL renderer with `xr.enabled=true`, a rig group, and calls `S.setAnimationLoop(or)`, so XR frames go through the same loop.
- The "Enter VR" button calls `qh().enter("immersive-vr")`, which calls `navigator.xr.requestSession(V,{optionalFeatures:["local-floor","bounded-floor","hand-tracking"]})`. Requesting everything as optional maximises acceptance.
- The fractal is a real heightfield (`Gh`, 4359): smooth escape-time values plus a 3×3 blur become vertex heights on a 5×3.5 m mesh, mounted on a pedestal in a circular "observatory". It counts as 3D, though it is a 2.5D relief rather than a volumetric fractal.
- Android Chrome: `immersive-vr` is usually unsupported, so the main button becomes "XR info" and "Enter AR" appears. AR shows the full opaque room with 6DoF phone tracking, which still meets "enter a virtual room".
- iPhone: there is no WebXR, so the user explores the same room on screen with orbit/pinch, a walk joystick and gyro "Motion look". `DeviceOrientationEvent.requestPermission` is handled in `fe`. The page is not stereo or immersive, which is a platform limit, and the XR dialog says so honestly.

## 2. Device/XR compatibility — 8
- **Sessions:** `isSessionSupported` is checked for both modes with `Promise.allSettled` (`st`, 4503). `devicechange` re-checks. Secure context and a missing `navigator.xr` produce explicit messages. DOMException names map to user-readable errors (`NotAllowedError`, `SecurityError`, …).
- **Reference space:** `local-floor` is tried first, falling back to `local` with the rig raised +1.65 m (seated or phone). `d.setReferenceSpace(P)` overrides three's default.
- **Input:**
  - Controllers: ray beam; session-level `select` handled in `Q` by computing the pose from `targetRaySpace` and multiplying by the rig matrix; teleport onto the floor plane; snap turn of 30° on the right stick with a latch and dead zone (`xt`).
  - Grip/squeeze summons the panel (`A`). Haptics are wrapped in a try.
  - Hands: `pinchend` (de-duplicated against session `select` by the per-source 320 ms debounce in `Y`), plus fingertip spheres.
  - `transient-pointer` (Vision Pro) and `screen` (phone AR) also flow through `Q`.
  - Gaze-dwell reticle (3 s) when no tracked pointer exists (`Bt`, `et>=3`).
- `setFoveation(.6)`, raised to `.9` under low fps; framebuffer scale 0.9 on touch devices.
- **Gaps:**
  - The AR session is visually identical to VR: an opaque 70 m sky sphere `new ri(70,32,20)` (4499), so passthrough is never visible.
  - `dom-overlay` is only requested when `domOverlayRoot` is passed, and `r0` never passes it, so that branch is dead.
  - On phone AR, `screen` inputs don't count as tracked, so the gaze-dwell reticle stays active. Something left under the centre of the screen for 3 s will fire, which could include "LEAVE XR".
  - No cardboard-style stereo fallback for iPhone.

## 3. Visual wow effect — 7
- **Terrain shader `i0` (4359):** a 16-bit height field packed into R/G of a `DataTexture` (decoding correctly uses `NoColorSpace`). Animated, antialiased isocontours via `fwidth`, a secondary band, rim light, specular, and slope-aware recolouring so cliffs don't streak. The set interior gets a dark "glass" top with a fine grid and sheen. Edge vignette, a reveal fade-in, and 3 palettes (Aurora, Nebula, Solar).
- **Atmosphere:**
  - Ambient effects: a floating spark `Points` field with per-point twinkle, additive "light columns" on boundary cells, a procedural nebula sky (3D value noise), 1,900 stars, and drifting dust.
- **Room (`Xh`, 4493):** 16 wall panels and beams, instanced ribs and light strips, emissive torus rings on floor, pedestal and ceiling, a floor shader with grid and pool glow, and canvas-text signage ("M A N D E L B R O T", the formula).
- ACES tone mapping at exposure 1.15.
- **Limits:**
  - Metallic `MeshStandardMaterial` (metalness 0.72–0.8) with no environment map renders mostly dark.
  - No bloom or glow post-processing, which is acceptable since post-processing is hard in WebXR.
  - In XR, auto quality drops to `low`: a 448×314 field and a 160×112 mesh, so fine filaments are lost.
  - Deep zoom only re-meshes the same 5×3.5 slab.

## 4. Usability & controls — 7
- **Outside XR:**
  - Boot progress screen; intro copy; dock with destination select, prev/next, palette, slow orbit, zoom, home, and a settings sheet (relief, scale, quality, pause, cinema mode, walk mode, motion look, sound, gentle motion).
  - Help and XR-capability dialogs. Double-click/double-tap dives into the clicked UV via a raycast (`j`), and the zoom math correctly keeps the picked point fixed.
  - WASD walking with wall/pedestal collision (`gt`). Orbit is clamped inside the room (`ae`).
  - `prefers-reduced-motion` honoured, ARIA labels, safe-area insets.
- **Inside XR:**
  - A 2.68 m panel with 9 buttons (palette, region, spin, relief ±, reset, zoom ±, leave) and hover halos; a hint line on the panel. Teleport with a floor marker; comfort-friendly snap turn rather than smooth locomotion; grip brings the panel in front of you.
- **Issues:**
  - In XR, "ZOOM IN" always zooms at the view centre (`case"scale-up": w.zoom(1.6)`). From the home view that dives into the black cardioid interior, and there is no way to point at the surface to dive.
  - The set's plateau is at world y ≈ 0.76 + 0.022 + 1.25 ≈ 2.03 m. That is above a standing user's eye height, so in VR the boundary detail is seen edge-on from below unless the user lowers relief.
  - The panel starts ~4.8 m away at the side (`panelAnchor:new F(-3.35,1.2,1.65)`).
  - Teleport is barred within 3.3 m of the pedestal centre.

## 5. Code quality & robustness — 7
- **Strengths:**
  - Escape-time compute runs in a Blob Worker built from `Gh.toString()`, with transferables. It falls back to a chunked main-thread compute on any worker error (`w()`, 4493).
  - A generation counter cancels stale jobs. Interior and cardioid/bulb early-out.
  - Adaptive quality lowers pixel ratio, foveation, then field quality when fps falls below 36 on screen or 55 in XR (`or`). Context-loss handlers. Full `dispose()` paths.
  - Session-start failure restores camera and rig state (`dt`). `try/catch` around all optional APIs.
- **Weaknesses:**
  - The application code itself is minified, so it is hard to audit, debug or modify. A "standalone file" did not require that.
  - The room is built from about 120 separate meshes: 56 tick boxes, 32 wall boxes, many tori. That is roughly 240 draw calls per XR frame without multiview, and the ticks and panels could be instanced.
  - Dead dom-overlay branch. The in-XR "SPIN" button silently does nothing when Gentle motion is on (`case"rotate": e||(r=!r)`).
  - Allocations per frame are minor (`yt.clone()` in motion-look slerp, `new F(0,1,0)` in walk).

## 6. Prompt adherence — 9
- Single HTML file with no external scripts, fonts or assets (the only URLs are SVG/XHTML namespaces and a citation in a three.js comment). three.js r186 is embedded under its MIT notice.
- Uses WebXR directly with a deliberate "Mandelbrot room" concept. The only deviation is that the app code is minified rather than readable source.

## Bugs found
1. **AR mode cannot show passthrough** (4499 `new ri(70,32,20)` sky sphere; 4503 `E.background=new Gt("#050b13")`). "Enter AR" on Quest/Pico/Android shows the same opaque room as VR, which makes the button misleading.
2. **`dom-overlay` never requested** (4503, `qh` handles `domOverlayRoot`, but the `qh({...})` call in `r0` omits it). Also `body.xr-active #ui` is hidden, so phone-AR users get no DOM controls and must use the in-world panel or the system back gesture.
3. **Gaze-dwell fires on phone AR** (4503, `xt`: `Tt` counts only `tracked-pointer`/hand/`transient-pointer`, not `screen`). The reticle stays active on phones, so holding a button in screen centre for 3 s activates it, including "LEAVE XR".
4. **XR zoom always targets view centre** (4503 `case"scale-up":return w.zoom(1.6)`, with no UV argument). From the home preset (centre −0.55+0i, inside the cardioid), repeated zoom-in lands on flat interior.
5. **Plateau above eye level in VR** (4503 `w.group.position.set(0,.76,-1.4)` + max height `.022+1.25` in `Gh`). Boundary detail is viewed edge-on from below at default relief.
6. **"SPIN / PAUSE" is a silent no-op with reduced motion** (4503 `case"rotate":e||(r=!r)`). There is no toast, unlike the 2D path's `lt()`.
7. Minor: `Math.PI/6` snap turn reads `axes[2]` and also accepts `handedness==="none"`. Fine for the xr-standard mapping, but a single-controller left-hand setup has no turn.

## Top 5 issues
1. **Major: the XR view hides the interesting part of the set.** The plateau tops out at ≈2.03 m (group y 0.76 + height 1.272) with the user standing at about 1.6 m. *Fix:* lower the group to ~0.35 m, or cap the default XR relief at ~0.55. Better, enable scale/relief on entry so the boundary rim sits at ~1.1 m.
2. **Major: no point-to-dive in XR.** `scale-up` calls `w.zoom(1.6)` without a UV, so XR users can only cycle 4 presets or zoom at centre, which from home lands in the black interior. *Fix:* in `ce()`, also raycast `w.mesh`. On select with a fractal hit, call `onAction("dive", hit.uv)` which maps to `w.zoom(2.4, uv)`, reusing the desktop logic.
3. **Major: "Enter AR" delivers an opaque room** (sky sphere and scene background drawn in AR). *Fix:* when `session.environmentBlendMode !== "opaque"` (or mode is `immersive-ar`), hide the sky, stars, walls and background and keep pedestal plus exhibit, giving a real mixed-reality tabletop. Or drop the AR button on headsets.
4. **Minor: phone-AR UX gaps.** Dom-overlay is never wired, and gaze-dwell can trigger accidental "LEAVE XR". *Fix:* pass `domOverlayRoot` (a small exit/palette overlay) and count `targetRayMode==="screen"` as a tracked input so dwell is disabled on phones.
5. **Minor: maintainability and XR draw-call budget.** The app code ships minified, and the room uses ~120 separate meshes. *Fix:* ship the app section unminified (only vendor minified), and instance the 56 ticks and 32 wall/beam boxes (`InstancedMesh`) or merge static room geometry.

## Strengths
1. Very thorough XR input coverage: controllers, hands with pinch de-duplication, transient-pointer, screen taps, gaze-dwell, haptics, grip-to-summon panel, teleport with bounds, comfort snap-turn.
2. Robust compute pipeline: Blob Worker with transferables and main-thread fallback, cancellation, interior early-outs, adaptive quality that also adjusts foveation in XR.
3. Correct, careful fractal maths: smooth escape-time, 16-bit height packing with correct `NoColorSpace` decoding, and zoom-to-point that keeps the picked point fixed.
4. Rich, polished 2D experience for non-XR devices (iPhone included): onboarding, help and capability dialogs, walk joystick, gyro look with iOS permission, reduced-motion support, ARIA.
5. Truly self-contained and offline-capable: zero network requests, with honest messaging about HTTPS and device limits.

## Verdict
A polished, robust and genuinely device-aware WebXR experience. It meets the done-when on Quest, Pico, PCVR and Android, with an honest touch/gyro fallback on iPhone, and its input handling is among the most complete you could expect from a single file. The visuals are good rather than jaw-dropping: dark metals with no env map, a 2.5D relief, and low resolution in XR. Two in-XR design gaps hold it back: the plateau sits above eye height, and you can't dive where you point.
