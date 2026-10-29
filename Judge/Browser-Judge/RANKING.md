# Browser Judge — blind ranking

## Ranking criteria

- **Works out of the box (30%)**: a recognisable 3D Mandelbrot in a room must appear on a plain desktop or phone browser without errors, because that is the "Done when" bar.
- **XR entry and fallback behaviour (20%)**: what Enter VR/AR does when no XR runtime is present (an honest in-page message, a disabled button, or a usable fallback) predicts how the page behaves on unsupported devices.
- **Usability and controls (20%)**: orbit, zoom/dive, presets and discoverable help decide whether a person can actually explore the set.
- **Visual quality against its prompt (20%)**: v1 is judged on "wow" effect; v0 is judged on a clear, legible 3D room. Each candidate is held only to its own prompt.
- **Phone-width layout (10%)**: the prompt names Android and iOS phones, so the UI must stay usable at about 390 px.

## Ranking

| Rank | Candidate | Prompt | Justification |
|---|---|---|---|
| 1 | H | v1 | Polished glowing observatory with contour-traced terrain. Destinations, palette, double-click dive and a rich Controls panel (walk, motion look, sound, gentle motion). Exemplary "XR info" capability dialog. ARIA labels throughout and a clean phone layout. No console errors. |
| 2 | C | v0 | Convincing room: plinth landscape, wall display with zoom-box minimap, in-world control signage and a tablet panel. Tour, shape and colour modes all work. Honest WebXR status text, no errors, usable at phone width. |
| 3 | G | v0 | Elegant observatory with clickable complex-plane minimap, destinations, palettes, detail levels, walk mode and a Cardboard-style stereo fallback. Disabled "VR unavailable" button, strong accessibility labels and a responsive phone UI. Its terrain is less striking than C's, and WASD did nothing in my test. |
| 4 | A | v1 | Striking pedestal landscape with live Julia-set inset, click-to-dive, auto-dive to Seahorse Valley and progressive refinement. Clear "no WebXR" message. The "Immerse" mode gave confusing camera views, and the toolbar overflows at phone width. |
| 5 | D | v1 | Most features: terrain/Mandelbulb/canyon modes, fly-to presets, sliders, D-pad and a toast on failed VR. The Mandelbulb is the wow moment, but the terrain is noisy and aliased, the phone UI covers the scene, and it depends on the Tailwind CDN. |
| 6 | E | v1 | Recognisable cardioid landscape once orbited, but the default view sees a tilted sheet edge-on, the info panel faces away (mirrored), there is no VR/AR button, and the "needs secure context" hint is wrong on localhost. |
| 7 | F | v1 | Clean start card with VR/AR/screen buttons, but VR/AR failures use native alert(). The screen view is a magenta extruded blob with no recognisable Mandelbrot, no controls, and the camera can pitch upside down. |
| 8 | B | v1 | Attractive landing page, but "Launch 3D room" only tries XR, logs NotSupportedError and suggests a "3D touch view" that never appears. No Mandelbrot is ever shown on desktop, so the done-criterion fails here. |

## Special elements

- **H — "XR info / Step inside" capability dialog**: it lists Interactive 3D room, Immersive VR, Immersive AR and Connection status per device and explains what headsets need, which is the most honest and helpful no-XR fallback of all eight.
- **G — Stereo (side-by-side) mode with a landscape hint**: it gives phones without WebXR, such as iOS Safari, a Cardboard-style VR experience, directly addressing the Apple-phone requirement.
- **A — Live Julia-set inset ("Julia set at the pointer")**: it updates as you hover the Mandelbrot terrain, adding real mathematical insight on top of the visuals.
- **C — In-world controls signage and a plinth-side tablet panel**: these put the help text and buttons inside the 3D room where a headset user can reach them, rather than in a DOM overlay XR cannot show.
- **D — Volumetric Mandelbulb mode**: the most visually spectacular single moment in the set, even though it is a 3D cousin of the Mandelbrot set rather than the set itself.
- **C, G, H, A — Guided tour / destination flights to Seahorse Valley**: animated flights to famous regions make deep zoom discoverable for first-time users.
- **F — Native alert() for "VR/AR is not supported"**: it is the only candidate whose failure path used a blocking native dialog, which is poor UX and blocks the page in a headset browser.

## Summary of tests and approach

I loaded each candidate in its own origin in a single Chrome tab I created (closed at the end) and read the console after a fresh reload. I clicked every start button and toolbar control and tried the main presets, palettes, dive/zoom, orbit by drag, scroll zoom and keyboard where offered. On each I pressed Enter VR/AR (or the equivalent) to see the no-XR behaviour. For B I also hid `navigator.xr` to simulate a non-XR browser, and the fallback still did not appear. The window manager refused to resize (innerWidth stayed at 1443), so I tested phone width by loading each URL in a 390×844 iframe. Console errors that appeared after that iframe swap came from my test harness tearing down the parent page and were not counted. I read no source code. Environment limits: there was no WebXR runtime or emulator, so no real XR session was entered, and the frame rate may be throttled. 16 screenshots are saved in `screenshots/`.
