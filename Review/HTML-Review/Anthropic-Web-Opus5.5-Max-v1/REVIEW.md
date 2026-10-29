# HTML Review — candidate-02

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Done-when fulfilment | 8 | Immersive VR and AR sessions place a 3D Mandelbrot heightfield "hologram" on a pedestal in a sky-domed arena; iPhones get a gyro and Cardboard fallback. It is an open arena, not an enclosed room. |
| 2. Device/XR compatibility | 8 | No required features, `local-floor`→`local` fallback, optional hand-tracking, transient-pointer, screen-space AR with hit-test and dom-overlay, xr-standard gamepads, WebGL2 float-format fallbacks. |
| 3. Visual wow effect | 9 | GPU perturbation deep zoom (~43 octaves), distance-estimate terrain, procedural nebula cubemap with env reflections and fresnel, ACES tonemap, palette cycling, glows, particles, build/scan animations, Julia inset. |
| 4. Usability & controls | 8 | Clear landing page, per-input-type help, a world-space panel that follows the head, grab-pan, two-hand zoom and rotate, tap-to-dive, history, guided "Dive" tour, haptics, audio. No comfort vignette. |
| 5. Code quality & robustness | 7 | Strong engineering (async PBO readback, adaptive GPU budget, scissored progressive rendering), but dense one-liner style, a leaked XR session on the error path, synchronous CPU probes and leftover debug hooks. |
| 6. Prompt adherence | 9 | Truly standalone: one file with zero external requests (raw WebGL2 + WebXR, no three.js) and an XR-first design. |

**Overall score: 8.5 / 10**

## Summary of what the file is
- 1826 lines and ~112 KB. A single inline IIFE script (L102–1823) that passes `node --check`. It has no CDN, import or network dependency (grep for `http`/`<link`/`import(` finds nothing).
- Custom matrix and quaternion helpers (L120–185) and 12 GLSL ES 3.0 programs (L214–592) on hand-written WebGL2. No engine.
- The fractal is computed into 640² / 160² float textures by `FS_MANDEL` (L241). It uses perturbation iteration with Zhuoran-style rebasing, a float64 reference orbit (`uploadRef`, L781), dual-number derivative distance estimation and interior detection. A height-mapped 256² disc mesh then displaces it (`VS_TERRAIN`, L354).

## 1. Done-when fulfilment — 8
- `detect()` (L1798) calls `isSessionSupported` for `immersive-vr` and `immersive-ar` and shows "Enter VR" / "Enter AR". `startXR()` (L1753) creates the session, `XRWebGLLayer` and reference space, then drives `onXRFrame` (L1725).
- In VR the scene has a procedural nebula skybox (`FS_SKYGEN`, L306), a reflective grid floor with animated rings (`FS_FLOOR`, L491), 8 emissive pillars, a halo ring, a pedestal (`drawRoom`, L1322), dust particles and the fractal hologram on the pedestal. "Immerse" (`toggleImmerse`, L1650) scales the landscape to 36 m around the user.
- In AR on headsets the hologram is auto-placed in front of the user (L1733). On Android phones in AR it uses hit-test reticle placement (L1735, `placeAR` L1645).
- On iPhones (no WebXR) the status text says so explicitly (L1810). The in-browser explorer offers "Look around" (DeviceOrientation with the iOS permission request, L1599) and a "Cardboard" side-by-side stereo mode (L1611, L1522).
- Deductions:
  - The "room" is an open arena (sky, floor, pillars) rather than an enclosed room.
  - The iPhone path is not a WebXR session and has no lens distortion.
  - WebXR needs HTTPS or localhost. This is correctly detected and explained (L1809), but it means the file cannot simply be opened from a plain-HTTP LAN server.

## 2. Device/XR compatibility — 8
- **Session features:** only `optionalFeatures` are requested: `local-floor` and `hand-tracking`, plus `hit-test` and `dom-overlay` for AR (L1758–1759). No required features, so nothing hard-fails. The `local` fallback with a −1.6 m offset is at L1767.
- **Quest 3 / Pico 4 Ultra:**
  - Controllers: trigger, grip and stick via `gamepadInput` (L1238), using the xr-standard indices `axes[2/3]` and `buttons[4/5]`.
  - Hands: `fillPoses`/`fillJointRadii` with a `getJointPose` fallback (L1252), rendered as joint spheres.
  - Other: haptics (L1183), `fixedFoveation = 0.5` (L1764), passthrough AR with an `alpha` layer and a clear alpha of 0 (L1742).
- **Gaze-and-pinch (Vision Pro style):** `transient-pointer` is handled, with thresholds (L1214) and help text (L1484).
- **Android phone AR:** `interactionMode === 'screen-space'` → `arHandheld`. It adds a viewer-space hit-test source, a DOM-overlay HUD and `beforexrselect` suppression on HUD taps (L1817).
- **GPU:** WebGL2 is required. A friendly error is shown if it is missing (L190). Texture format degrades RGBA32F → RGBA16F → RGBA8 depending on `EXT_color_buffer_float` / `OES_texture_float_linear` (L193, L706). The sky resolution is reduced on touch, Quest and Pico devices (L720).
- **Risks:**
  - `gamepadInput` falls back to `axes[0]/[1]` when fewer than 4 axes exist (L1241). Any non-xr-standard gamepad, possibly including Chrome's screen-space AR input source, would be read as a thumbstick.
  - Steam Frame is only covered generically, which is fine.

## 3. Visual wow effect — 9
- **Fractal fidelity:**
  - The perturbation engine reaches `MIN_SPAN = 2.5e-13` (~2^43 zoom), with adaptive `maxIter` up to 16000 from CPU float64 probe percentiles (L805).
  - Heights come from a normalised log distance estimate (L276–279), so ridges trace the boundary instead of showing escape-time staircases.
  - Interior points are flagged via the period-derivative test and shaded as glossy black glass with env reflections and specular (L409).
- **Shading:**
  - Finite-difference normals with correct non-uniform-scale handling (`uK`, L380–384), Lambert lighting, fresnel cubemap reflections, ACES-style tonemap.
  - Analytic anti-aliased iso-lines from the phase (`fwidth`, L393–399), palette cycling, a radial "pulse" when a refined tile lands (L406), a scan line while computing (L413) and a rim-light build-up ring (L412).
  - A skirt mesh gives the hologram a solid edge (L421–449).
- **Atmosphere:**
  - Domain-warped fbm nebula with 3 star layers baked into a mipmapped cubemap, one face per frame (L1441).
  - Floor rings, a volumetric-looking tube glow (`FS_GLOW` mode 0), 1400 dust motes, 240 sparks, distance fog that hides the edge in immersive mode (L415–416), and a live Julia set for the pointed-at c.
- **Smooth transitions:**
  - van Wijk–Nuij optimal zoom paths (`zoomInterp`, L930).
  - A collapse/rebuild animation for long jumps (L960–968).
  - Cross-fading between fractal tiles (`disp.mix`).
- **Missing:** bloom/post-processing and true shadows. Glow is faked additively.

## 4. Usability & controls — 8
- **Onboarding:** the landing copy adapts to device capability (L1806–1811), and a timed hint shows on explore entry (L1699).
- **In-XR panel:** a canvas texture with 10 buttons, readouts, a progress bar and context help that changes with the input type (L1483–1485). It sits beside the pedestal and swings to face the user, follows the head yaw in immersive mode (L1051–1067), and freezes while hovered.
- **Interaction model:**
  - Select-tap dives ×3 (`tapZoom`).
  - Select or grip and drag pans on the grabbed height plane (`updateGrabs`, L1207).
  - Two grabs zoom and twist the hologram (L1227–1235).
  - Stick-Y zooms toward the hit point; stick-X rotates.
  - A/X = Back, B/Y = Immerse.
- **Browser and phone:** orbit, pinch-dolly, grab-pan, wheel zoom-at-cursor, keyboard shortcuts (L1586), gyro look and Cardboard mode.
- **Extras:** generative ambient audio with depth-dependent filter and chimes (L1136), a history stack, the guided tour of famous locations, and table-height auto-adjust to the user's head (L1732).
- **Weaknesses:**
  - Immersive-mode zoom flights scale the world around the user with no vignette or comfort option.
  - The XR help text never mentions the A/X / B/Y shortcuts or stick-X rotation.
  - In Cardboard mode a tap always dives, and the only exit is the DOM bar.

## 5. Code quality & robustness — 7
- **Good:**
  - Async 128² height readback via PBO + `fenceSync` with no pipeline stall (`doReadback`, L900), used for CPU ray-marching against the hologram (`hitTerrain`, L1017).
  - An adaptive per-frame GPU iteration budget driven by frame-time jitter (`adaptBudget`, L1462).
  - Scissored progressive tile rendering (`runJob`, L824).
  - A tile cache scored by coverage and effective resolution (`score`/`chooseDisplay`).
  - Graceful fatal messages for WebGL2, shader and FBO failures.
  - Frame loops are separated correctly: window rAF stops while `xrSession` is set and restarts in `onXREnd`.
- **Weak:**
  - Extremely dense code, often 150–250 characters per line with many statements, so it is hard to review or maintain.
  - Uncaught errors become a full-screen fatal banner (L117), even for non-fatal ones.
  - No WebGL context restore (L1820).
  - Debug leftovers: `window.__mxr` (L1822) and `evLog` (L1189).
  - `startJob` runs up to 81 float64 probes × up to 16000 iterations synchronously on the main thread (L803). Up to ~1.3 M JS iterations on a new full job can cause XR frame hitches at deep zoom.
  - Per-frame allocations (arrays in `xfP`, `views`, `{o,d}` rays, `[...inputs.values()]`) are minor GC pressure.

## 6. Prompt adherence — 9
- The file is a single standalone HTML with no external resources at all. It uses WebXR and puts XR first while still providing a good non-XR path.
- The iOS fallback deviates from WebXR by necessity, and the page explains this (L1810).

## Bugs found
1. **Leaked XR session on setup failure** (`startXR`, L1760–1785). If `navigator.xr.requestSession` succeeds but a later step throws (`makeXRCompatible`, layer creation, both reference-space requests), the `catch` never calls `s.end()`. The session stays active with no `requestAnimationFrame`, so the user is stuck in a black or frozen immersive view.
2. **Non-xr-standard gamepads read as thumbsticks** (`gamepadInput`, L1241). With fewer than 4 axes the code uses `axes[0]/[1]` as the stick. A screen or touch input source that exposes touch-position axes, or any 2-axis device, would trigger continuous zoom or rotation while touched.
3. **Previews suppressed during path flights** (`schedule`, L873–874). The full destination job starts immediately and `if (job …) return;` blocks preview jobs. During a zoom-out or panning flight, the uncovered part of the disc fades to flat through `covg()` until the 640² job finishes, which shows as visible blank edges.
4. **Fullscreen and orientation lock after an await** (`toggleStereo`, L1613–1617). Both are called after awaiting the motion-permission prompt, so transient user activation may be consumed. iPhone Safari also supports neither, so Cardboard mode on iPhone stays portrait with browser UI, and the toast tells the user to turn the phone sideways.
5. **Squeeze and select share one grab slot** (`pressLogic`/`beginGrab`, L1196). Pressing squeeze while a select-grab is active on the same controller overwrites `s.grab`. On release of the first button the grab kind no longer matches, so the original press is silently lost.
6. **Error handler is too broad** (L117). Any uncaught error, including a benign error from a promise or extension, shows a permanent "Something broke" banner over the UI.
7. **Contextual help is incomplete** (L1483–1485). It omits the A/X (Back), B/Y (Immerse) and stick-X (rotate) bindings.

## Top 5 issues
| # | Severity | Location / evidence | Suggested fix |
|---|---|---|---|
| 1 | major | `startXR` L1760–1785: no `s.end()` in the `catch` after a successful `requestSession` | Keep a reference to the session and call `s.end()` in the `catch`. Set `xrSession` before the awaits, or wrap the post-request setup in its own try/catch. |
| 2 | major | `startJob` L803 + `uploadRef` L781: synchronous CPU probes with caps up to 16000 iterations run inside the XR frame | Cap probe iterations for preview jobs, spread probes across frames, or move probes and the reference orbit to a Worker. |
| 3 | minor | `gamepadInput` L1241: fallback to `axes[0]/[1]` | Only read sticks when `gp.mapping === 'xr-standard'` and `targetRayMode === 'tracked-pointer'`. |
| 4 | minor | `schedule` L874: no preview jobs during path flights | Allow a cheap preview job while the destination full job is pending, or render the flight's bounding region as the preview. |
| 5 | minor | Comfort in immersive mode: `toggleImmerse` + `flyTo` world-scaling around the user, no vignette | Add a fading vignette or tunnel during flights in immersive VR, or snap zooms with a short fade. |

## Strengths
1. A genuinely deep-zoom renderer in a single file: GPU perturbation with rebasing, distance-estimate heights and interior detection, with honest claims ("forty doublings" ≈ the 2^43 limit).
2. Broad, carefully reasoned input coverage: controllers, hands with joint rendering, transient-pointer, screen-space AR with hit-test and DOM overlay, mouse, touch, gyro and Cardboard.
3. A rich, cohesive aesthetic: procedural nebula cubemap, reflective rings floor, glows and particles, palette cycling, build and pulse animations, Julia inset and generative audio.
4. Performance-aware architecture: async readback, progressive scissored tiles, an adaptive budget, a tile cache with cross-fade, and sky generation spread over frames.
5. Zero dependencies and a clear device-aware landing page that explains what is and isn't possible (secure context, iOS).

## Verdict
This is a technically ambitious, dependency-free WebXR experience. Its fractal engine (perturbation deep zoom with distance-estimated terrain) and atmospheric presentation should deliver a strong wow effect on Quest and Pico headsets and on Android AR, with sensible fallbacks for iPhones. The main weaknesses are robustness and maintainability: a session leak on setup failure, main-thread probe hitches at deep zoom, and very dense code. None of these block the core done-when scenario.
