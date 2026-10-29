# Browser + HTML Judge — blind ranking

## Ranking criteria

1. **Core goal met (30%)**: a recognisable 3D Mandelbrot set inside a room, reachable on desktop/phone without errors; this is the "done when" condition.
2. **XR readiness, judged from source (20%)**: a correct session setup (reference-space fallbacks, layer/viewport use, AR alpha, input handling), because no XR device or emulator was available.
3. **Visual quality / wow (20%)**: v1 asks for this explicitly; for v0 it only counts as polish, so a v0 entry is not marked down for lacking it.
4. **Usability and fallbacks (15%)**: clear Enter VR/AR behaviour when XR is missing, phone layout, touch/keyboard controls, no native dialogs.
5. **Mathematical depth / exploration (10%)**: zoom depth, presets/tours, precision. These decide whether the set is explorable or just a static prop.
6. **Prompt fidelity and robustness (5%)**: v0 must use three.js; "standalone" files should not depend on a CDN; no console errors.

## Ranking

| Rank | Candidate | Prompt | Justification |
|---|---|---|---|
| 1 | G | v1 | Raw WebGL2 with perturbation zoom (float64 reference orbit, rebasing): Dive reached 2×10¹⁰ with detail intact. Smooth fly-to, Julia preview, Immerse walk-in mode, hit-test AR, Cardboard and gyro fallbacks, honest XR status. No errors. On phones the toolbar scrolls sideways. |
| 2 | H | v0 | Bundled three.js room with plinth terrain, a live wall-screen map and an in-world control panel. The tour reached width 3×10⁻⁹ at 4,450 iterations, crisp. Shapes, palettes, gyro/phone-headset modes, clear "no runtime" note. Looks less spectacular than G. |
| 3 | B | v1 | Best-looking room: a lit gallery rotunda, a contour-lined pedestal and a polished HUD. The XR-info dialog explains device support; phone layout is clean; the settings panel is rich. Zoom is shallow (about 187×), and Seahorse renders as a large flat plateau. |
| 4 | C | v0 | Bundled three r186 gallery with destinations, palettes, a clickable minimap, a joystick walk mode, split-screen stereo and two AR modes. Polished and error-free, but the relief turns spiky at Seahorse and the hero text crowds the scene. |
| 5 | E | v1 | Most "wow" colour: a raymarched Mandelbulb, terrain and cathedral modes, presets, auto-dive, a spatial UI panel. But it loads three r128 and Tailwind from CDNs (not standalone), the terrain aliases into noisy spikes, the Mandelbulb isn't the Mandelbrot set, and the panel swamps phones. |
| 6 | D | v1 | Hand-written WebGL2 with strong XR input code: grab, pinch, locomotion, adaptive quality. In the browser, though, the in-world help panel renders mirrored, the default camera is edge-on, and the terrain looks washed out. Without XR there is no button or explanation, only hint text. |
| 7 | A | v1 | Minimal WebGL2 heightfield: a blocky pink mesa of the set with three flat colours, a floor and stars. No zoom, presets or room. It uses two native `alert()` calls for missing XR, advertises pinch-to-zoom but doesn't implement it, and the AR clear is opaque. |
| 8 | F | v1 | No recognisable Mandelbrot appears: the raymarcher hits almost nothing, leaving wavy backdrop stripes and purple specks under permanent hero text. The XR path reads a non-existent `view.viewport`, ignores eye projections, and derives an inverted forward vector. |

## Special elements

- **G, perturbation deep zoom**: a float64 CPU reference orbit with Zhuoran rebasing let the Dive button run to 1.96×10¹⁰ while the terrain still rendered, far past the roughly 10⁵ limit where plain float32 shaders break down.
- **H, deep tour with float64 reference orbit and PBO readback**: the tour stop "Seahorse valley" at width 3×10⁻⁹ rendered crisp spirals on both the wall screen and the terrain, and async readback keeps ray-picking from stalling the frame.
- **H, wall-screen map with a viewport rectangle**: projecting the current window onto a wall-sized 2D map turns the room itself into the navigation aid.
- **B, XR capability dialog**: instead of a dead button or an alert, "XR info" lists 3D/VR/AR/secure-context status per device, the most honest desktop fallback in the set.
- **C, split-screen stereo plus a joystick walk mode**: a phone-headset fallback with a lens-distortion caveat lets non-WebXR phones (iOS) still get a stereo room.
- **G and H, local-floor/hit-test/dom-overlay session setup with Cardboard and gyro fallbacks**: both pick features per mode and hide unsupported buttons, so each phone class gets a working path.
- **D, XR input design**: thumbstick locomotion, hand-tracking pinch-grab via joint distance, squeeze-scale and frame-time-driven quality steps are the most thorough controller code, even though the flat view is buggy.
- **E, CDN dependency**: loading three r128 and the Tailwind CDN script means the "standalone" file renders nothing offline, a real risk on headset browsers with a flaky connection.
- **A, native `alert()` dialogs (2)**: missing VR/AR is reported through blocking `alert()` calls, the only candidate to use native dialogs.
- **F, SDF misuse in a full-screen raymarcher**: a min/max of iteration-count bands is not a distance field, so the march misses the set entirely, a single shader decision that produced an empty scene.
- **D, mirrored world-space panel**: the help panel faces the XR rig spawn point, so the desktop orbit camera sees its text reversed (`D-initial-mirrored-panel.jpg`).

## Summary of tests and approach

I read each `index.html`. For the bundled builds (B, C, H) I skimmed past the three.js bundle and grepped the minified app code for session setup, input and fallbacks. Before testing I grepped every file for `alert/confirm/prompt` and found only A, with two calls. In one Chrome tab I loaded each localhost origin and stubbed the native dialogs after every load. I read the console, clicked Enter VR/AR (no XR device, so every candidate's unsupported path was exercised), and used each candidate's controls: presets/tours, dive, palettes, walk/immerse, stereo, orbit by dragging, zoom by wheel. I also tested at a phone-like 446 px width, the window manager's minimum. Deep-zoom claims were checked against on-screen readouts (G 1.96×10¹⁰, H width 3×10⁻⁹). Limits: no WebXR emulator, so XR quality was judged from source; frame rate wasn't measured reliably. Sixteen screenshots are in `screenshots/`. Each candidate was judged against its own prompt version, so the v0 entries (C, H) had to use three.js, which both bundle inline.
