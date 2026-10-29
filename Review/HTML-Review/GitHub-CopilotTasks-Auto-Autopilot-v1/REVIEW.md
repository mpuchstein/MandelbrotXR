# HTML Review — candidate-04

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Done-when fulfilment | 2 | The XR render loop throws after its first frame (`frame` parameter shadows the function, l.163/167), so no device gets a working immersive room. Only the non-XR orbit view works. |
| 2. Device/XR compatibility | 3 | It asks for `immersive-vr`/`immersive-ar` with `xrCompatible`, but `local-floor` is required with no fallback, there is no XR input at all, AR is cleared opaque, and iPhone gets only the flat fallback. |
| 3. Visual wow effect | 3 | A 120×120 CPU heightfield in three hard colour bands, simple diffuse/rim shading, 650 point "stars" and a flat floor plane. The viewer spawns under a plateau 1.85 m high. |
| 4. Usability & controls | 3 | The landing panel is good-looking, but XR has no controls, no exit button and no locomotion. The hint promises pinch-zoom that isn't implemented, and Explore mode has no way back to the menu. |
| 5. Code quality & robustness | 3 | Compact raw WebGL2 with shader error checks. But it has a fatal shadowing bug, a per-view full-framebuffer clear, no try/catch in `enter()`, canvas resize on every frame, and a stale XR framebuffer binding. |
| 6. Prompt adherence | 6 | A true single file with no dependencies that uses WebXR, but it falls far short of "highest possible wow" and the "virtual room". |

**Overall score: 2 / 10**

## Notes per criterion

### 1. Done-when fulfilment
- `enter()` (l.169–176) starts the loop with `xrSession.requestAnimationFrame(frame)` at l.175, and there `frame` is the function. Inside `function frame(t, frame)` (l.163), the second parameter (the `XRFrame`) shadows the function name. So `xrSession.requestAnimationFrame(frame)` at l.167 passes an `XRFrame` object, which throws a TypeError, and the loop never runs a second time. A quick check confirms it: `function frame(t, frame){ typeof frame }` → `"object"`. The user gets one frame and then a frozen or black immersive view on every headset and on Android AR.
- Even with that fixed, stereo VR would still be broken. `draw()` calls `gl.clear(COLOR|DEPTH)` (l.155) once per view, with no scissor test, and `gl.clear` ignores the viewport. Drawing the right eye therefore wipes the left eye of the side-by-side framebuffer, leaving one eye black.
- Only "Explore on screen" (l.183–190) works: a mouse/touch orbit camera around the terrain. That isn't an immersive room.

### 2. Device/XR compatibility
- Good: `getContext('webgl2', {xrCompatible:true})` (l.52). `isSessionSupported` is checked before `requestSession`, and the optional features include `local-floor`, `bounded-floor`, `hand-tracking` and `dom-overlay` (l.172). That request shape is fine for Quest 3, Pico 4 Ultra and Steam Frame browsers.
- `requestReferenceSpace('local-floor')` (l.175) is mandatory even though the feature was optional. There is no fallback to `local`, so a rejection leaves an immersive session open with no loop and an unhandled promise rejection.
- AR: `alpha:false` (l.52) plus an opaque clear colour on every view (l.155) hide the camera passthrough on Android ARCore and Quest passthrough. The `arMode` argument is passed but never used (l.154/166).
- No XR input handling at all: no `inputSources`, no `select`/`squeeze` events, and `hand-tracking` is requested but never used. No gaze or transient-pointer handling either.
- iPhone: there's no `navigator.xr`, so both XR buttons are disabled (l.178) and only the flat view remains. That fallback is acceptable on its own, but the pinch zoom advertised in the hint doesn't exist there.
- Phones and VR: Android Chrome mostly reports `immersive-vr` unsupported, and the response is an `alert()` (l.171). The secure-context requirement isn't mentioned or detected.

### 3. Visual wow effect
- The fractal is sampled on the CPU at 121×121 vertices over 10.5 m (l.133–137), with 72 iterations and smooth escape-time height. Detail is coarse, at about 9 cm per vertex.
- Colour comes from a three-step band (l.118: pink / blue / navy), not a smooth palette, so the fractal's colour structure is lost. The intro text says "the black hole at its heart is the Mandelbrot set" (l.39), but the set itself is drawn bright pink (`h > .83`).
- Shading is a single point light with `pow(...,.35)` "glow", an up-vector rim and a time pulse (l.76–83). There is no fog, bloom, post-processing, reflections or animation of the fractal.
- The "room" is one flat 42 m plane at about y = −2.59 m (l.138, l.158): below the real floor, with no walls. Around it is a ring of fixed-pixel-size points (l.140, l.87).
- Placement: the terrain centre (c = −0.68+0i, inside the cardioid) sits at height 1.85 m (computed: `h*2.5-.65 = 1.85`). The XR origin is at the terrain centre with no offset, so a standing user's head (~1.6 m) is under the plateau, looking at its unculled underside, and the terrain bottom lies about 0.6 m below the real floor.

### 4. Usability & controls
- The landing panel (l.13–43) looks polished and has clear buttons. The XR buttons are relabelled "NOT DETECTED" when there's no `navigator.xr`.
- Inside XR there's no interaction, no exit button, no locomotion and no way to scale or reposition the fractal.
- Screen mode: drag to orbit, wheel to zoom, double-click to reset (l.184–188). Pinch zoom is promised by the hint (l.45) but not implemented. The only touch gesture is a one-finger drag, and `pointerup` ignores `pointercancel`.
- After "Explore" hides the panel there is no way back to Enter VR or AR without reloading.
- Errors are shown via `alert()`, which works poorly inside headset browsers.

### 5. Code quality & robustness
- Structure is compact (about 145 lines of JS, one IIFE, `'use strict'`) and shader compile/link errors throw with the info log (l.92–100). The script passes `node --check`.
- `enter()` has no try/catch. A failing `requestSession`, `updateRenderState` or reference-space request becomes an unhandled rejection, and a half-initialised session is never ended.
- Inside `frame()`, `if (!pose) return;` (l.164) also skips re-scheduling, so one frame of lost tracking would kill the loop even once the shadowing is fixed.
- `screenFrame` calls `resize()` every frame (l.189). Assigning `canvas.width`/`height` reallocates the WebGL drawing buffer on each frame, which hurts performance on phones.
- After an XR session ends, the binding is never reset with `gl.bindFramebuffer(gl.FRAMEBUFFER, null)`, and the viewport is left at the per-eye value. Returning to screen mode renders into the dead XR framebuffer.
- Each `draw()` allocates new matrices (`I()` and an IIFE that builds the room model matrix, l.157–158), plus `mul()`/`inverse.matrix` per view, so there is avoidable GC pressure in the XR loop.
- Blending is on while depth writes stay enabled for the soft point sprites (l.155/159), so the transparent corners of the sprites occlude stars behind them.
- Explore is wired twice, via `onclick` (l.183) and `addEventListener` (l.190). It works, but it's confusing.

### 6. Prompt adherence
- It is genuinely standalone: no CDN or external assets, raw WebGL2 and WebXR. That is a legitimate choice.
- The "highest possible visual wow" and the "virtual room" are barely attempted, and the core XR path doesn't work.

## Bugs found
1. **l.163/167**: the `frame(t, frame)` parameter shadows the callback name, so `requestAnimationFrame` gets an `XRFrame` and throws. The XR loop dies after one frame.
2. **l.155 (called per view at l.166)**: the full-framebuffer `gl.clear` inside the per-view loop erases the previous eye, so only the last view is visible in stereo.
3. **l.164**: an early `return` on a null pose skips the next `requestAnimationFrame`, so losing tracking permanently stops rendering.
4. **l.175**: `local-floor` is required with no `local` fallback and no try/catch, so the session can be left open with no render loop.
5. **l.52 + l.155**: `alpha:false` and an opaque clear in AR hide the passthrough, so AR shows a solid scene with no camera feed. `arMode` is unused.
6. **l.133–138, l.158**: scene placement relative to the XR origin. The user spawns inside or under a 1.85 m-high plateau, and the "room" floor sits 2.6 m below the real floor.
7. **l.45 vs l.184–188**: "pinch to zoom" is advertised but not implemented, and `pointercancel` isn't handled.
8. **l.189**: `resize()` runs every frame and reallocates the drawing buffer each time.
9. **l.173 / l.189**: after XR ends, the framebuffer and viewport are never reset for screen rendering.
10. **l.39 vs l.118**: the text calls the set a "black hole", but the code colours it bright pink.

## Top 5 issues
1. **Critical: the XR loop dies after its first frame** (l.163, l.167). Rename the parameter (`function onXRFrame(t, xrFrame)`) and call `session.requestAnimationFrame(onXRFrame)` at the start of the callback.
2. **Critical: one eye is blank in stereo** (l.155 called per view). Clear once per frame after binding the layer framebuffer, before the view loop, or enable `SCISSOR_TEST` with a per-view scissor.
3. **Major: the user spawns under the fractal plateau and the room is a lone sub-floor plane** (l.133–138, l.158). Lay the fractal out as a floor-level table or diorama about 1–2 m in front of the user, place the floor at y = 0, and build actual walls or a dome with smooth palette colouring.
4. **Major: no XR interaction, no fallback reference space, no error handling** (l.169–176). Wrap `enter()` in try/catch, fall back from `local-floor` to `local`, handle `select`/`squeeze` and controller rays for zoom/pan, and add an in-XR exit.
5. **Major: AR is opaque and phone controls are incomplete** (l.52, l.155, l.45). Clear with alpha 0 in `immersive-ar` (context `alpha:true`), skip the room geometry there, implement two-pointer pinch zoom, and stop resizing the canvas every frame.

## Strengths
- A true single file with zero dependencies. Raw WebGL2 keeps the payload tiny (13 KB).
- Correct basics for starting XR: `xrCompatible` context, `isSessionSupported` check, a sensible list of optional features, and `XRWebGLLayer` with `depthNear`/`depthFar`.
- Smooth escape-time height and finite-difference normals give a plausible fractal heightfield.
- A polished, responsive landing panel with feature detection that disables the XR buttons when WebXR is missing.
- A non-XR "Explore on screen" fallback with orbit, zoom and reset, so iPhone and desktop users see something.

## Verdict
The candidate is a tidy-looking but very thin raw-WebGL prototype. Its immersive path is broken: a name-shadowing bug kills the XR frame loop after one frame, and a per-view clear would blank one eye even if the loop ran. On top of that, the scene puts the viewer under the fractal, has no XR input, and makes AR opaque, so the done-when criterion is not met on any headset or phone. Only the flat on-screen orbit view works.
