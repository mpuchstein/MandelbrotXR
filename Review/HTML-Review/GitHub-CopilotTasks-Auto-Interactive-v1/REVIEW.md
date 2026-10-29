# HTML Review — candidate-05

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Done-when fulfilment | 2/10 | A VR/AR session starts, but the XR rendering is broken: each eye sees a different half of the image, the camera faces backwards, pitch is inverted, and there is no actual room. |
| 2. Device/XR compatibility | 3/10 | Requests immersive-vr/ar with local-floor, but ignores `view.projectionMatrix`, has no controller/hand input, no `local` fallback, and iPhones get only an inline orbit view. |
| 3. Visual wow effect | 4/10 | The neon raymarched glow slab could look nice on a flat screen, but it marches a non-distance field, colours by integer iteration counts (banding), the "stars" are stripes, and there is no room. |
| 4. Usability & controls | 2/10 | Desktop and touch orbit/pinch work. In XR there is no input, no exit UI and no fractal navigation, and the hints promise features that don't exist ("tap to place", ESC). |
| 5. Code quality & robustness | 3/10 | Compact, syntax-valid raw WebGL, but the XR camera math is wrong, the shader costs about 8k Mandelbrot iterations per pixel, and a failed session start leaves the session hanging. |
| 6. Prompt adherence | 6/10 | A true standalone single file with no dependencies that uses WebXR, but "virtual room" and "highest wow / good usability" are not delivered. |

Static checks: the file is 138 lines and 11.5 KB with no external resources. The inline script (lines 45–136) passes `node --check`. Grepping for `projectionMatrix`, `inputSources`, `select`, `gamepad`, `keydown`, `framebufferScaleFactor`, `fixedFoveation`, `hit-test` and `clear(` finds nothing.

## 1. Done-when fulfilment — 2
- `beginXR` (l.123–132) starts `immersive-vr` or `immersive-ar` and drives `session.requestAnimationFrame`, so a headset user does enter *something*.
- What they see is not usable stereo 3D:
  - `draw()` sets `uniform r` to the **full framebuffer** size (l.106, l.111). The shader builds `uv` from window-relative `gl_FragCoord` (l.71). In a side-by-side stereo framebuffer, the left eye renders only the left half of the virtual image plane and the right eye only the right half. The two eyes diverge by about ±20° and cannot fuse.
  - The forward vector (l.110) is the quaternion applied to **+Z**, but WebXR views look down **−Z**. The rendered camera faces backwards. Yaw happens to stay consistent, but pitch is inverted: look down and the horizon moves down.
  - `right`/`up` are rebuilt from world-up (l.110), so head roll is ignored.
  - The projection is a hard-coded `zoom=1.18` (l.111), giving about 46° vertical FOV. The headset's real FOV is about 90–100°, and `view.projectionMatrix` is never used. The world will not appear locked in space, which is a strong nausea trigger.
- There is no room. The scene is a starfield (`backdrop`, l.66–69) plus a horizon glow line (l.91–92). There are no walls, floor or furniture.
- With the `local-floor` origin, the fractal slab sits at floor level (|y| < 0.33) under the user's feet. Because pitch is inverted, the user has to look *up* to see it.

## 2. Device/XR compatibility — 3
- **Quest 3 / Pico 4 Ultra / Steam Frame:** `immersive-vr` with `local-floor` is fine for these headsets, but the stereo and projection bugs above affect all of them. `immersive-ar` passthrough is offered when supported (l.134), and alpha output is used for `alpha-blend` (l.94, l.111).
- **Input:** `hand-tracking` is requested (l.126) but there is no `inputSources`, `select` or gamepad handling anywhere. Controllers and hands do nothing.
- **Reference space:** `requestReferenceSpace('local-floor')` (l.128) has no fallback to `local`. If it is rejected (possible on some phone AR stacks), the session has already started and `state.xr=true` has stopped the inline loop. The catch only writes a status line, never calls `session.end()`, and no `end` listener has been attached yet, so the user is stuck in a frozen session.
- **Android AR:** `dom-overlay` with `root: document.body` (l.126) puts the WebGL `<canvas>` itself inside the overlay. Its last inline frame was drawn with alpha=1, so it may cover the camera feed. The overlay is also pointless, because `#ui` is hidden on entry (l.128).
- **iPhone:** Safari has no `navigator.xr`, so clicking only shows "WebXR unavailable — explore in 3D touch mode" (l.124). The inline orbit/pinch view is a reasonable fallback, but there is no device-orientation look-around and no AR Quick Look.
- **No-VR browsers (desktop, many phones):** the button is relabelled "Launch 3D room" (l.134) but still calls `beginXR('immersive-vr')`, which fails with "XR could not start".
- There is no secure-context check or message for `file://` or `http://` loads.

## 3. Visual wow effect — 4
- **Technique:** a single fullscreen-triangle raymarcher (l.70–95) renders a "thick extrusion of the Mandelbrot boundary". `scene()` takes the band where the iteration count is near 24 and intersects it with a sinusoidally "breathing" slab (l.58–65). Accumulated glow (l.78) and exponential tonemapping (l.93) give it a neon look.
- **Distance field:** `boundary=abs(m-24.0)/24.0` is a piecewise-constant integer step function, not a distance.
  - The side walls of the band are discontinuities, so `|d|<.003` (l.79) is rarely met there. Rays either pass through or exhaust the 96 steps with `hit<13`, which is then shaded as a hit (l.82). Expect noisy, aliased walls.
  - Finite-difference normals of a step function (l.84) are zero or degenerate on those walls.
- **Colouring:** `hue` uses integer `m` (l.85) with no smooth or continuous escape count, so colours band. Only 80 iterations are used and there is no zoom, so the fractal is shallow.
- **Stars:** the `stars` term (l.67) depends mainly on `rd.x`, so it produces vertical streaks rather than points.
- **Room:** none; see criterion 1.
- On a 2D screen it probably reads as a glowing sci-fi slab. In a headset the rendering bugs undo the effect.

## 4. Usability & controls — 2
- **Landing page:** good copy and typography, and a loading veil (l.23–24, l.30–43).
- **Desktop/touch:** drag to orbit, wheel or pinch to change distance (l.116–122). Pinching also orbits, because the pointer drag runs at the same time. `pointercancel` is not handled.
- **In XR:**
  - No input of any kind, and no in-world UI or exit button.
  - No way to zoom, pan or change iterations or palette. "Exploring" the set is impossible.
- **Misleading hints (l.42):** "AR: point at a surface · tap to place" is not implemented (no hit-test). "ESC: return to the portal" has no handler.
- **Comfort:** the inverted pitch and diverging stereo are the worst possible outcome.

## 5. Code quality & robustness — 3
- **Positives:** a tidy IIFE with `'use strict'`, a WebGL null check (l.50) and an XR try/catch.
- **Performance:**
  - Each pixel runs up to 96 march steps × 80-iteration `mandel()`, plus 6 more `scene()` calls for the normal and one `mandel()` for colour. That is about 8,000 complex iterations per pixel.
  - The XR framebuffer is at default scale (about 2k×2.2k per eye on Quest 3, roughly 9 M pixels), with no `framebufferScaleFactor`, foveation or dynamic resolution.
  - Expect single-digit fps on standalone headsets and phones. The inline view is capped at DPR 2 (l.114) but is still heavy.
- **Error paths:**
  - Shader compile or link errors `throw` (l.96–98) before the loading veil is dismissed (l.135). The page then sits on "INITIALIZING FRACTAL FIELD" forever with no message.
  - The `isSessionSupported('immersive-vr')` promise has no `.catch` (l.134).
- **Minor:** unused `rot`/`PI` in the shader. `resize` compares the integer `canvas.width` with a float `w` (l.114).

## 6. Prompt adherence — 6
- It meets the hard constraints: one self-contained HTML file, no CDN, uses WebXR, has a phone fallback.
- It misses the soft goals: no virtual room, a modest wow effect, and poor usability in XR. Building on raw WebGL instead of a library is defensible for size but is the root of the hand-rolled camera bugs.

## Bugs found
1. **l.71 + l.106/111:** `uv` uses window `gl_FragCoord` with `r` set to the full framebuffer. Each eye renders only half of the image plane, so the stereo diverges and cannot fuse.
2. **l.110:** forward = q·(+Z) instead of q·(−Z). The camera faces backwards and pitch is inverted.
3. **l.110:** `right`/`up` are derived from world-up, so head roll is ignored.
4. **l.111:** fixed `zoom` replaces `view.projectionMatrix`. FOV and scale are wrong, and asymmetric frusta are ignored.
5. **l.127–131:** a session-start failure after `requestSession` (for example `local-floor` rejected) leaves the session running with no rAF loop and no `end()`, so the user is stuck.
6. **l.126:** `dom-overlay` root is `document.body`, which includes the WebGL canvas. This can occlude the AR camera feed on Android, and the overlay UI is hidden anyway (l.128).
7. **l.134:** when VR is unsupported the button is relabelled "Launch 3D room" but still requests `immersive-vr` and errors.
8. **l.42:** the hints advertise "tap to place" and ESC behaviour that don't exist.
9. **l.62/79/82:** a non-metric, piecewise-constant field is raymarched, so step-exhaustion counts as a hit and the side walls are noisy.
10. **l.96–98 / l.135:** a shader error leaves the loading screen up permanently with no message.
11. **l.67:** the "stars" render as vertical stripes.
12. **l.117–122:** two-finger pinch also triggers orbit, and `pointercancel` is not handled, so the drag can get stuck.

## Overall score: 2.5 / 10 (rounded: 3)

## Top 5 issues
1. **Critical: broken stereo.** l.71/l.111: `r` is the full framebuffer size while `gl_FragCoord` is window-relative.
   - Fix: pass the per-view viewport offset and size, and compute `uv=(gl_FragCoord.xy-vp.xy-.5*vp.zw)`. Better, build rays from `inverse(view.projectionMatrix)` and `view.transform.matrix`.
2. **Critical: backward camera and inverted pitch.** l.110.
   - Fix: use the rotation matrix's −Z column for forward, its X column for right and its Y column for up, straight from `view.transform.matrix`, so roll is honoured too.
3. **Critical: performance unusable on standalone HMDs and phones.** l.57/75/84: about 8k iterations per pixel at full XR resolution.
   - Fix: precompute the escape-time field into a texture or heightfield mesh, or march a smooth distance estimate (`|z|log|z|/|dz|`).
   - Also set `framebufferScaleFactor` to about 0.5, enable `fixedFoveation`, and reduce steps.
4. **Major: no room and no XR interaction.** l.66–92, no `inputSources` use.
   - Add actual room geometry: floor, walls, a pedestal for the fractal.
   - Add controller/hand `select` and `squeeze` plus thumbstick for zooming and panning the fractal, and an in-world exit button.
   - Fix or remove the false hints at l.42.
5. **Major: fragile session start and fallbacks.** l.127–134.
   - Try `local-floor` and fall back to `local`. Attach the `end` handler before any awaits, and call `session.end()` on failure.
   - Make the "Launch 3D room" path not request VR.
   - Give iOS a device-orientation look-around mode.

## Strengths
- Truly standalone: about 11 KB, zero dependencies, loads instantly.
- A polished landing page with a good typographic hierarchy and mobile media query.
- A reasonable inline fallback (orbit plus pinch) for devices without WebXR, such as iPhone.
- Offers passthrough AR when supported, with alpha output for `alpha-blend`.
- An interesting artistic idea: a glowing, breathing extrusion of the iteration band with glow accumulation and tonemapping.

## Verdict
This is a tiny, dependency-free page with an attractive landing screen and a glowing raymarched slab that probably looks decent on a flat screen. The WebXR path itself is fundamentally broken: each eye renders a different half-image, the camera points backwards with inverted pitch, the projection ignores the headset's own, and frame cost is far beyond what standalone headsets and phones can run. There is also no room and no in-XR interaction, so the done-when criterion is not met in practice.
