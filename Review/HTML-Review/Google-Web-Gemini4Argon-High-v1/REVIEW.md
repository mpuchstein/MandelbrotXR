# HTML Review — candidate-08

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Done-when fulfilment | 7 | `immersive-vr`/`immersive-ar` sessions with a 3D-displaced Mandelbrot terrain on a pedestal in a lit "sanctuary". iPhones only get a non-immersive orbit view. |
| 2. Device/XR compatibility | 6 | Generic controller, hand-pinch and gamepad handling, plus AR passthrough. But it pins old three r128, has no dom-overlay or hit-test for phone AR, gives no hint about HTTPS, and needs the network for three CDNs. |
| 3. Visual wow effect | 7 | Per-pixel fractal shading with derivative micro-normals, spec/fresnel, orbit traps, a raymarched Mandelbulb, a room-scale "canyon" mode, a grid floor and particles. The terrain relief collapses at deep zoom. |
| 4. Usability & controls | 6 | Rich HTML deck, a spatial canvas UI that the laser can operate, presets and auto-dive. Vertical pan is inverted, the spatial UI fires twice on phone taps, and VR locomotion is hidden behind a mode toggle. |
| 5. Code quality & robustness | 5 | Clean, well-sectioned IIFE that passes `node --check`. Costly CPU raycasts against a 115k-triangle plane every XR frame, a fragment loop of up to 1024 iterations, duplicated listeners, and no CDN/error fallback. |
| 6. Prompt adherence | 7 | One HTML file using WebXR, as asked. It relies on Tailwind's dev CDN, three.js and Google Fonts from the network, so it isn't truly standalone, and the file doesn't say why. |

## 1. Done-when fulfilment — 7
- `launchWebXR(mode)` (l.1777) checks `isSessionSupported` and then calls `requestSession` with `optionalFeatures: ['local-floor','bounded-floor','hand-tracking','layers']` (l.1796). Called from button clicks, so a user gesture is present.
- Inside XR the user is placed at `userRig.position.set(0,0,2.35)` (l.1804), in front of a pedestal (l.879–984). The Mandelbrot set is a vertex-displaced 241×241 plane (`terrainGeo`, l.1006; displacement in the vertex shader, l.1053–1091). That is genuinely 3D.
- The "room" is a grid floor shader, 8 pillars with neon strips, ceiling rings and a starfield dome (l.741–874). It has no walls, so it reads as an open platform more than a room, but it is a coherent virtual space.
- In AR (l.1807) the background, fog and `roomGroup` are hidden, which works as a passthrough hologram on Quest 3, Pico and Android.
- iPhone Safari has no WebXR, so iOS users get only the non-XR orbit view plus an optional gyro "magic window" (`toggleGyroscope`, l.2002). That is an acceptable fallback, but not an immersive room.

## 2. Device/XR compatibility — 6
- **Good:**
  - Controllers come from `renderer.xr.getController(i)` and are parented to `userRig` (l.1580–1629).
  - Select and squeeze events are handled, and so are hand pinches, because pinch arrives as `select`.
  - Thumbsticks are read from `gamepad.axes[2/3]` (l.1747), which follows the xr-standard mapping (Quest, Pico, SteamVR-class).
  - Both hands held together give a two-hand zoom (l.1683).
  - Touch, mouse, wheel, keyboard and iOS `DeviceOrientationEvent.requestPermission` are all handled.
- **Weak:**
  - three.js **r128** (2021) comes from cdnjs (l.10). Requesting the optional `'layers'` feature routes r128 into its early projection-layer/MSAA path on browsers that expose `renderState.layers`. That is a compatibility and performance risk on Quest and Pico; it would not show up on hardware testing.
  - Phone AR requests no `dom-overlay`, so the HTML UI vanishes in a phone AR session. Phone users must tap the small 3D panel and leave via system back.
  - No `hit-test` and no anchors: the hologram sits at a fixed offset.
  - Hands get no rendered models: there is no `getHand`, and the procedural "wand" is drawn at the pinch ray instead.
  - Nothing mentions the secure-context (HTTPS) requirement. On plain http, `navigator.xr` is undefined and the toast says only "WebXR not detected".
  - The AR button is shown even where AR is unsupported. That is handled with a toast, so it's fine.

## 3. Visual wow effect — 7
- **Terrain fragment shader** (l.1140–1233):
  - full per-pixel iteration up to 1024
  - smooth colouring
  - a derivative `dz` is tracked but never used for a distance estimate
  - micro-normals from `dFdx/dFdy(smoothIter)` blended with screen-space geometric normals
  - two diffuse lights, Blinn spec and cyan fresnel rim
  - animated "energy veins"
  - orbit-trap glow in the interior
  - a holographic rim ring
  - four cosine palettes that also re-tint the room lights, floor, particles and strips (`cyclePalette`, l.2113)
- **Mandelbulb mode** (l.1246–1403): a sphere-bounded raymarch (64 steps, 8 DE iterations) with step-count AO and a halo glow. **Cathedral mode** expands the terrain 4.2× into a bowl around the user (l.1078–1083). **Julia morph** animates `c` along a path (l.2313).
- **Fidelity problems:**
  - Vertex height uses at most 96 iterations (l.1034), normalised to 96. At the presets (zoom 95–620×) most vertices hit the cap and drop to the flat 0.18 "plateau" (l.1069), so the 3D relief mostly disappears exactly where the detail is.
  - `ridge = sin(pi*pot)` goes to 0 as pot → 1 and then jumps to 0.18 in the interior, so the set is ringed by a moat/cliff artefact instead of "boundary mountains".
  - Everything is float32. Auto-dive runs to 95,000× (l.2300), where pixel spacing (~3e-8) nears float precision around |c|≈0.74, so blockiness shows up late in the dive.
  - No bloom or post-processing. The glow is faked by additive materials, which keeps it cheap for XR.

## 4. Usability & controls — 6
- **Good:**
  - Polished glass HUD with live coordinates and FPS, a hide-UI toggle, a d-pad with hold-to-zoom, 5 presets with smooth fly-to (exponential lerp, l.2306), auto-dive, and a palette button.
  - Inline instructions (l.439–442).
  - The spatial canvas panel (l.1409–1570) has 16 laser-hit buttons with hover highlights and a telemetry footer.
- **Problems:**
  - **Vertical pan is inverted relative to horizontal** for mouse and touch drag (l.1900–1901, l.1961–1962) and for VR grab (l.1735). Horizontal follows the hand; vertical moves against it.
  - Two-finger pan (l.1987–1988) ignores `orbit.theta`, so after orbiting it pans in the wrong direction.
  - Phone taps on the 3D panel trigger actions twice (see Bugs).
  - The XR hover highlight only redraws every 0.5 s, because `renderSpatialUICanvas` runs from the FPS block (l.2285), so laser feedback lags.
  - Thumbstick defaults: in "fractal" mode both sticks zoom and pan Re only, with no Im pan, and both sticks act at once. Locomotion needs the "STICK" button on the panel. There is no snap or smooth turn, despite the comment at l.664.
  - Cathedral mode at the XR spawn point (z = 2.35) puts the canyon surface at roughly 0.4 m plus ridge height up to ~1.4 m above the floor. The user stands inside the geometry.
  - The panel sits about 3.3 m away at the user's left (l.1410). Reachable with the 4.5 m laser, but there is no recentre or "summon panel" option.
  - No in-XR onboarding beyond the panel subtitle; toasts are DOM-only and invisible in XR.

## 5. Code quality & robustness — 5
- Readable structure: one state object, numbered sections, shared uniforms. The extracted script passes `node --check`.
- **XR frame-loop cost:**
  - `updateXRInteractions` calls `raycaster.intersectObject(fractalTerrainMesh)` for each controller every frame (l.1706). The mesh is 240×240 segments, about 115k triangles, so pointing at the hologram costs a full JS triangle sweep per controller per frame. That is a real risk to 72–90 Hz on Quest.
  - New `Vector3`s are allocated every frame (l.1684–1685, l.1732, l.1760–1763).
- **GPU cost:** the terrain fragment loop runs up to 1024 iterations (presets 420–640), interior pixels pay the full count, and the material is transparent and DoubleSide. In Cathedral mode it covers most of both eyes, with no foveation or framebuffer-scale tuning.
- **Raycasts hit undisplaced geometry:** the reticle and grab land on the flat plane at y=0.84, not on the visible mountains. In Cathedral mode the visible 4.2×-scaled bowl can't be hit at all.
- **Missing robustness:**
  - If the three.js CDN fails there is no error handling and the page is blank.
  - Tailwind's Play CDN is not meant for production and logs a console warning.
  - If `renderer.xr.setSession` throws, `currentXRSession` stays set (l.1799 vs l.1834), and the next click calls `end()` on a dead session.
  - Each gyro enable adds another `deviceorientation` listener (l.2023).
  - `window.onload` gates the loop. That's fine, but fonts used by the canvas UI may not be loaded on the first draw.

## 6. Prompt adherence — 7
Single HTML file using WebXR, VR and AR, aimed at headsets and phones. Three runtime CDN dependencies (Tailwind JIT, three r128, Google Fonts) undercut "standalone": offline the page breaks, and there is no inlined fallback. The extra modes (Mandelbulb, Julia) go beyond the brief, but the Mandelbrot terrain stays the default, so that's acceptable. The file doesn't say why it uses CDNs.

## Bugs found
1. **Double-firing spatial UI on phone taps:** the canvas `touchstart` (l.1933) doesn't call `preventDefault`, so a tap fires `touchend` → `checkSpatialUIClick` (l.1994), then the browser's emulated `mousedown`/`mouseup` → `checkSpatialUIClick` again (l.1912). Toggles cancel out (auto-dive, Julia, stick mode), the palette skips one, zoom applies 1.85² ≈ 3.4×.
2. **Inverted vertical pan:** im grows toward −z (PlaneGeometry rotated −90°). `targetIm -= dy*cos` (l.1901/1962) and `targetIm -= delta.z*panScale` (l.1735) move the content against the drag on that axis, while the horizontal axis follows the drag.
3. **Two-finger pan ignores camera azimuth** (l.1987–1988).
4. **Raycasts against undisplaced/unscaled geometry:** terrain and Cathedral picking (l.1661, l.1706) don't match what's rendered.
5. **Vertex-height cap of 96 iterations** (l.1034) flattens the terrain at all non-overview presets, and the `ridge→0 / interior=0.18` discontinuity (l.1068–1071) makes a moat around the set.
6. **Stale `currentXRSession`** if `setSession` rejects (l.1799, l.1834).
7. **Duplicate `deviceorientation` listeners** on every gyro re-enable (l.2023).
8. **Thumbstick handling** (l.1753): in "fractal" mode both hands apply zoom and pan together, and the Im axis is unreachable by stick.
9. **Spawn inside Cathedral geometry:** in Cathedral mode at z=2.35, the user's position is below the canyon surface (l.1082–1083 vs l.1804).
10. **Hover feedback throttled to 2 Hz:** `renderSpatialUICanvas` runs only in the FPS block (l.2285), so the laser hover highlight lags.

## Overall score: 6 / 10

## Top 5 issues
1. **Major: per-frame CPU raycast against a 115k-triangle mesh for each controller** (l.1704–1706).
   - Fix: raycast against a low-poly proxy (a 2-triangle plane or disc at the pedestal), or compute the ray–plane intersection analytically.
   - Skip the fractal raycast when the UI was hit.
2. **Major: GPU cost risks dropped frames on Quest and Pico** (l.1155 loop up to 1024 iterations; presets at 420–640; transparent DoubleSide; Cathedral fills the view).
   - Fix: cap the XR iterations (~256), add cardioid/bulb early-out for interior points, and turn off `transparent` where alpha isn't needed.
   - Use `renderer.xr.setFramebufferScaleFactor` or foveation on a newer three.js.
3. **Major: 3D relief disappears at deep zoom** (l.1034, l.1068–1071).
   - Fix: base height on log-normalised smooth iteration with a higher vertex cap (or a distance estimate), and make it continuous with the interior plateau.
   - Pick the vertex cap per zoom.
4. **Major: input bugs.** Double-firing taps on phones (l.1912/1994): call `preventDefault` in `touchstart`, or use Pointer Events with one handler. Inverted vertical pan (l.1735/1901/1962): flip the Im sign so it follows the drag. Two-finger pan should rotate by `orbit.theta`.
5. **Minor-to-major: CDN dependence and old three r128 with `'layers'` requested** (l.8–14, l.1796).
   - Fix: inline or pin a current three.js build and drop `'layers'`.
   - Add a load-error message and an HTTPS/secure-context hint.
   - For phone AR, add `dom-overlay` so the HTML deck is available.

## Strengths
1. Strong fragment shading for the terrain: smooth colouring, derivative micro-normals, spec/fresnel rim, orbit-trap interior glow, palettes that re-tint the whole room.
2. Three distinct 3D modes (pedestal terrain, raymarched Mandelbulb, room-scale canyon) plus an animated Julia morph and auto-dive.
3. A real in-XR interface: the canvas-texture spatial panel with laser hit-testing, hover state and a telemetry footer, plus grab-to-pan and two-hand zoom.
4. Covers VR and AR passthrough, with a usable non-XR fallback (orbit, touch pinch, keyboard, gyro with the iOS permission flow).
5. Clean, well-commented single-IIFE structure with smooth exponential interpolation of all fractal parameters.

## Verdict
This is a visually ambitious entry with real WebXR VR and AR entry, a working in-headset control panel and good-looking shader work, so the done-when bar is basically met on Quest, Pico and Android. The frame-loop cost (dense-mesh raycasts and very long per-pixel loops), the terrain that flattens at deep zoom, and several input bugs (inverted vertical pan, double taps on phones) hold it back. The CDN dependencies and r128 add compatibility risk that the source alone can't rule out.
