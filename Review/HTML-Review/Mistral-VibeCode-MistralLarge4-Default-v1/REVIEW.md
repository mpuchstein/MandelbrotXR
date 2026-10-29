# HTML Review — candidate-03

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Done-when fulfilment | 6/10 | VR headsets do get a 3D room with a height-field Mandelbrot, but you spawn facing away from it, and phone AR places it 3.9 m behind you. |
| 2. Device/XR compatibility | 5/10 | Solid basics (`xrCompatible`, `local-floor`→`local`→`viewer`, hand joints, iOS permission button), but `select` is wired to the session, screen/transient input does nothing, and magic-window orientation is off by 90°. |
| 3. Visual wow effect | 6/10 | Raw-WebGL2 height-field relief, ACES tonemap, fog, fresnel, glowing cylindrical room, 1400 additive particles, but colours only at vertex resolution and the lighting rotates with the mesh. |
| 4. Usability & controls | 3/10 | Spawn orientation, mirrored grab and fly, zoom that stops past ~16×, no pan in VR, no fractal zoom on phones, drag-to-orbit nearly unreachable, hidden Exit button. |
| 5. Code quality & robustness | 4/10 | Compact and dependency-free, but several real state bugs (framebuffer and viewport clobbered mid-frame), GPU leaks on quality change, unused EMA, unhandled rejections. |
| 6. Prompt adherence | 9/10 | One self-contained HTML file, no CDN or library, uses WebXR VR and AR plus a flat fallback. |

Static checks: the 755-line inline script (lines 63–817) passes `node --check`. The file is 819 lines and 42 KB, with no external resources. I checked the rig and placement math numerically with the file's own `m4Mul`, `m4T` and `m4RotY`.

## 1. Done-when fulfilment — 6
- **VR (Quest / Pico / Steam Frame):** `startSession('immersive-vr')` (l.606) builds a room: floor disc, ceiling, a 7 m cylinder wall, a pedestal and a rotating ring (l.266–271, `renderScene` l.433–449). The Mandelbrot is a displaced 256² grid driven by an escape-time texture (`MESH_VS` l.99–108), so it really is 3D. But the start rig is `rigPos=[0,0,2.4], rigYaw=Math.PI` (l.386). I checked this numerically: an identity head looks along world **+Z**, away from the pedestal at the origin and away from the instruction panel at z = −1.75 (l.243). The user faces a dark wall and has to turn round to find the content.
- **Android phones (AR):** the AR auto-placement (l.564–569) takes the viewer position in reference-space coordinates and writes it into world space, which is then shown through the π-rotated rig. Computed result: the object sits at **(0, 1.3, +3.9)** in the viewer's space, which is behind the user. The room isn't drawn in AR (`S.mode!=='ar'`, l.433), so the user sees only sparkles in front of them.
- **iPhone:** there is no WebXR. The user gets the flat "magic window" with a motion-permission button (l.803–811). It is a 3D view of the room on screen, not an immersive one, which is acceptable as a fallback.

## 2. Device/XR compatibility — 5
- Good: the context is created with `xrCompatible:true` (l.71). The session requests `optionalFeatures` `local-floor`, `bounded-floor`, `hand-tracking`, `dom-overlay` (l.608) and retries without `domOverlay` (l.610–614). The reference space falls back through `local-floor` → `local` → `viewer` (l.618–622). Thumbstick input reads xr-standard `axes[2/3]`, `buttons[0/1/4]` (l.500–512). Hand-tracking pinch uses the `thumb-tip` / `index-finger-tip` joint distance (l.503–509). The iOS `DeviceOrientationEvent.requestPermission` flow works (l.803).
- Bad: `selectstart`/`selectend` set `e.target._sel` (l.624–625). `e.target` is the **XRSession**, not `e.inputSource`, so `src._sel` (l.513, 515–516) is never true. As a result, phone-AR screen taps, Vision Pro transient-pointer and gaze-select do nothing.
- Bad: even with select fixed, screen sources have no `gripSpace`, so `p` stays null (l.515) and a grab cannot happen.
- Bad: `quatFromDeviceOrientation` (l.374–378) leaves out the standard −90° X correction for "camera looks out of the back of the device". Holding the phone upright (β≈90°) points the camera at the ceiling. Android fires `deviceorientation` without a permission prompt, so this hits Android flat mode automatically. The absolute α heading is also never zeroed, so the starting yaw is arbitrary.
- `isMobile` (l.74) matches Quest/Pico user agents, which contain "Android", so headsets start at reduced quality. That is harmless but probably not intended.
- `'layers'`, `'handedness'` and `'passthrough'` are not standard feature descriptors. They are ignored, so this is noise only.

## 3. Visual wow effect — 6
- Height comes from smooth escape time, `h=pow(f,0.35)` (l.94–95), stored in a 1024² RGBA16F render target (l.300–332). The mesh is lit with diffuse, Blinn specular, fresnel rim, a point glow and an animated scan band (l.113–126). Everything is ACES-tonemapped and fogged. The room has a glowing grid floor with rings, wall light strips, a ceiling halo ring, a pulsing emissive torus, and rising, twinkling particles (l.137–161). For a hand-rolled renderer it is cohesive.
- Fidelity loss: colour is sampled **in the vertex shader** (`vC=c4.rgb`, l.107) and interpolated. The fractal's colour detail is therefore capped at the mesh resolution (256², or 192² on mobile and headsets), not the 1024² texture. `vUv` is passed to the fragment shader but never used to sample.
- The normal `vN` stays in object space (l.107) while `uLight` and `uCam` are world space. With auto-yaw (l.553) and the −0.55 rad tilt, highlights and shading turn with the object instead of staying put.
- The interior of the set is a flat black pit at h = 0, with a cliff at the boundary. Clear, but the set itself has no relief.
- The tilted plate (RotX −0.55, half-size 1.1) dips about 0.57 m below its 0.5 m centre and clips through the pedestal top and the floor.
- There is no bloom or post pass; the "glow" is just bright tonemapped colour.

## 4. Usability & controls — 3
- The in-VR instruction panel is a nice touch (canvas texture, l.273–298, fades after 26 s or on grab). But it is fixed in the world **behind** the spawn direction.
- **Zoom freezes:** `setHalf` (l.391) only sets `texDirty` when `baseMaxIter()` changes. `maxIter` is clamped to 320–760 (l.390). Below `half≈0.106` (~16×) or above 1.7 the texture is never redrawn. The XR right stick (l.540) and the `+/-` keys (l.759–760) stop having any visible effect.
- **No pan in VR:** `cx/cy` only change in the flat two-finger handler (l.723–724). In XR you can only zoom around the fixed point (−0.75, 0).
- **Phones can't zoom the fractal at all:** pinch and wheel change `camDist` (camera dolly, l.716, l.741). Fractal zoom is keyboard-only.
- **Drag to orbit is nearly unreachable:** the hit test is a sphere of radius `1.6*objScale` (l.690). At the default camera (distance ≈3.39 m) that covers about 28° of angular radius against a ±30° vertical FOV, so most drags move the fractal. On a portrait phone the horizontal half-FOV is about 16°, so practically every touch hits it.
- **Grab and fly are mirrored in XR:** controller and joint positions (`p`, l.505–515) and `headFwd` (l.495) are in reference-space coordinates. They are applied directly to world-space `objPos` and `rigPos` (l.525, l.545) without the rig transform. With `rigYaw=π` the fractal moves opposite to the hand, and "Trigger: fly forward" flies backward. Smooth turning (l.535) also pivots around the rig origin, not the head.
- **The Exit button is never visible:** `#hud` is the dom-overlay root, but it gets `.hidden` (`display:none !important`) on entry (l.627). `#btnExit` (l.40) can never be shown.
- WASD in the flat view is rotated 90° (l.757–758): W moves +X and D moves +Z. The `f`/`r` vectors computed on l.753 are unused.
- Comfort: smooth locomotion at 2.1 m/s, smooth turning, and free 3D flight, with no snap-turn or vignette.
- If neither VR nor AR is supported but `navigator.xr` exists (desktop Chrome), both buttons silently disappear with no explanation.

## 5. Code quality & robustness — 4
- Positives: no dependencies, small hand-written math library (correct column-major `m4Mul`, `viewFromPosQuat`, `m4Invert`), shader compile and link errors shown in the UI (l.76–79), a float render-target completeness check with RGBA8 fallback (l.319–330), and adaptive render scale for flat mode (l.785–788).
- **Framebuffer and viewport clobbering:** `renderMandel()` is called from inside `renderScene` (l.427). It ends with `bindFramebuffer(null)` and leaves the viewport at `texSize×texSize` (l.407, l.416). In XR this happens inside the per-view loop (l.575–582), so on any frame with a texture update the **first eye draws into the canvas instead of the XR layer**. That frame's left eye shows only the clear colour, so continuous zooming flickers or blanks the left eye. In flat mode every pan frame renders the scene into a 1024² viewport (stretched and cropped).
- `applyQuality()` (l.592–596) creates a new grid VAO and buffers each time without deleting the old ones, which leaks GPU memory. `adjustQuality(dt*1000)` (l.585) uses one raw frame time, ignoring the `emaMs` it just computed (l.584). On a 72 Hz display dt≈13.9 ms never meets the <12.5 ms upgrade threshold, while one spike downgrades.
- `startSession`: if `XRWebGLLayer` or the final `viewer` reference-space request throws (l.616–621), the rejection is unhandled and the session is left running with no frame loop.
- In XR, `canvas.width/height` are set to the XR framebuffer size (l.628), which allocates a large unused default framebuffer.
- Per-frame `Float32Array` allocations in `m4Mul`, `m4Invert` and `modelMatrix` cause minor GC pressure in the XR loop.
- `window.__dbg` is left exposed (l.816).
- `floatOK` needlessly requires `OES_texture_float_linear` (l.300); RGBA16F is filterable in core WebGL2. Where that extension is missing (some mobile GPUs), the code drops to RGBA8, and 8-bit heights give coarse normals.

## 6. Prompt adherence — 9
It is a single standalone HTML file with no external scripts, fonts or assets, built on the real WebXR API in `immersive-vr` and `immersive-ar` with a non-XR fallback. Using raw WebGL2 instead of a library is a legitimate choice and keeps the file at 42 KB. The secure-context requirement is explained in the HUD (l.59).

## Bugs found
1. **XR spawn faces away from the content:** `rigYaw: Math.PI` (l.386, also `resetView` l.396). The head looks along world +Z, with the fractal and panel behind.
2. **AR object placed behind the user:** l.564–569 writes reference-space coordinates into world space under the π-rotated rig. Verified result: (0, 1.3, +3.9) in viewer space.
3. **Grab, fly and turn ignore the rig transform:** l.495, 505–515, 525, 545, 535. The hand and fractal move in mirrored directions, and the trigger flies backward.
4. **`renderMandel` clobbers the bound framebuffer and viewport mid-frame:** l.406–417, called at l.427 inside the per-eye loop l.575–582. The left eye goes blank or flickers whenever the texture updates; the flat view is distorted while panning.
5. **Zoom doesn't redraw past the maxIter clamps:** `setHalf` (l.391) sets `texDirty` only when maxIter changes, and maxIter is clamped at l.390.
6. **Select events stored on the session:** `e.target._sel` (l.624–625) should be `e.inputSource._sel`. Screen and transient-pointer input is dead.
7. **Exit button hidden:** `hud.classList.add('hidden')` (l.627) hides the dom-overlay root, including `#btnExit`.
8. **Device-orientation quaternion missing the −90° X correction and α offset** (l.374–378). The flat view on Android looks at the ceiling when the phone is held upright.
9. **Mesh normals not transformed by the model matrix** (l.107 vs l.113). The lighting is wrong once yawed or tilted.
10. **Colour sampled per vertex** (l.107): fractal detail is limited to the grid resolution.
11. **Drag hit-sphere covers almost the whole view** (l.690), so orbiting is effectively unavailable on phones.
12. **WASD axes rotated 90°** (l.757–758).
13. **GPU leak in `applyQuality`** (l.594); quality check uses raw `dt` instead of `emaMs` (l.585).
14. **Plate clips through the pedestal and floor:** tilt −0.55 rad on a 2.2 m plate centred at y = 0.5 (l.384, 421–423).
15. **Unhandled rejection in `startSession`** if the layer or last reference-space request fails (l.616–621).

## Overall score: 5/10

## Top 5 issues
1. **Critical: wrong rig orientation and coordinate spaces in XR.** Evidence: `rigYaw=Math.PI` (l.386); reference-space poses used as world coordinates (l.495, 515, 525, 545, 567). VR users spawn facing a blank wall, grab and fly are mirrored, and phone AR puts the fractal behind the user. **Fix:** start with `rigYaw=0` and the rig at +Z. Transform every input pose and head vector by `rigMatrix()` before applying it to `objPos`/`rigPos`, and compute AR placement in world space.
2. **Major: `renderMandel()` inside the per-eye loop rebinds framebuffer `null` and changes the viewport** (l.416, l.427, l.575–582). The left eye blanks or flickers while zooming; the flat view distorts while panning. **Fix:** render the texture once per frame before binding `layer.framebuffer` and setting per-view viewports, or restore the previous FBO and viewport after it.
3. **Major: fractal exploration is crippled.** Zoom stops redrawing beyond the maxIter clamps (l.390–391), there's no pan in XR, and phones have no fractal zoom (pinch = camera dolly, l.716). **Fix:** set `texDirty=true` unconditionally in `setHalf`. Map pinch to `half` (or add a toggle), add a stick or drag pan in XR, and zoom toward the pointed or grabbed location.
4. **Major: input wiring.** `select` is stored on the session (l.624–625), there's no screen or transient-pointer interaction, the drag hit-sphere swallows orbit gestures (l.690), and the Exit button is hidden (l.627). **Fix:** use `e.inputSource`. For `targetRayMode==='screen'`/`'transient-pointer'`, raycast from `targetRaySpace` against the plate. Hit-test the actual plate plane. Hide only `#top`/`#hint` in XR so the overlay Exit button survives.
5. **Major: visual fidelity left on the table.** Colour comes from the vertex fetch (l.107), and normals are in object space under a rotating model (l.107, l.113). **Fix:** sample `uTex` with `vUv` in the fragment shader, and compute the normal in the fragment shader from texture differences, transformed by `mat3(uModel)`.

## Strengths
1. Truly standalone: hand-written WebGL2 renderer, 42 KB, no external dependencies, the script parses cleanly.
2. Sensible XR plumbing: `xrCompatible` context, reference-space fallback chain, `dom-overlay` retry, xr-standard gamepad mapping, hand-joint pinch detection, adaptive quality hooks.
3. The fractal is really 3D: an escape-time height field rendered into a half-float target, re-rendered only when dirty, which is cheap for the XR frame budget.
4. Cohesive sci-fi room styling: grid floor with glow rings, wall light strips, halo ceiling, pulsing torus, drifting particles, ACES tonemap and fog.
5. Thoughtful onboarding pieces: an in-VR instruction panel that fades, an iOS motion-permission button, and secure-context advice in the HUD.

## Verdict
This is a compact, dependency-free WebXR renderer with a genuinely 3D height-field Mandelbrot and an attractive procedural room, and the XR session setup is broadly correct. One rig-orientation mistake undermines it: reference-space poses are mixed with world space, so VR users spawn facing away, grab and fly are mirrored, and phone AR places the fractal behind the viewer. On top of that, a framebuffer-state bug blanks one eye during zoom, and fractal zoom and pan are broken or missing on most inputs. It reaches the done-when bar on headsets only if the user turns round, and the usability falls well short of the brief's "good usability" goal.
