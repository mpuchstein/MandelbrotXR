# Browser Review — candidate-02

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Loads & renders | 9 | Fully self-contained (~656 KB inline, zero network requests); the first frame arrived in under 3 s; the console had zero messages over the whole session. |
| 2. Done-when (desktop-checkable) | 8 | A real "observatory" room (pedestal, columns, ring, wall typography) holds a 3D escape-time relief of the set; the XR path is gated and explained. Actual entry can't be tested here. |
| 3. Visual wow | 7 | Polished, museum-like art direction with glowing rings and banded neon terraces. But the flat, raised interior plateaus become big dark slabs that dominate the zoomed destinations. |
| 4. Usability & controls | 8 | Rich and coherent: destinations, palette, zoom, home, dive, walk mode, sliders, guide, keyboard. A few rough edges (focus swallows shortcuts, the hero text never leaves orbit mode). |
| 5. Robustness | 8 | No errors; resize and phone layout are clean; a steady 60 fps at every quality tier after reload. One unexplained 2–3 fps spell in the first session. |
| 6. XR readiness & messaging | 8 | When unsupported, the Enter VR/AR buttons are replaced by an "XR info" sheet with a clear per-capability table and guidance. In-XR interaction is documented (teleport, snap turn, grip panel, gaze dwell) but couldn't be verified. |

Environment: desktop Chrome on Linux with an AMD RX 6650 XT (ANGLE/OpenGL ES 3.2), viewport 1203×928, no XR device and no WebXR emulator. `navigator.xr` exists and is a secure context; `isSessionSupported` returned false for both `immersive-vr` and `immersive-ar`.

## Steps performed

1. **Loaded http://localhost:8765/ in a new tab and waited 3 s.** The full scene rendered: a dark circular hall with glowing teal rings and columns, curved "MANDELBROT" wall text, and the heightfield relief of the whole set on a pedestal. A hero overlay reads "The infinite room.", plus an exhibit caption, a hint line and a bottom toolbar (screenshot 01).
2. **Read the console and reloaded with tracking on.** No messages at all: no errors, no warnings. The navigation load event fired at ~171 ms. There are no external resources, so the HTML is truly standalone.
3. **Measured the frame rate with rAF timing.** In the first session I measured only 1.7–3 fps (max frame time 600–900 ms) with the page visible and focused. After switching quality tiers, and on every later reload, it held a steady **60 fps** (max frame 17 ms) on Light, Balanced, Fine and Automatic, sampled from 2 s to 16 s after load. The early slow spell couldn't be reproduced, so it is most likely environmental, but it's worth noting.
4. **Opened Controls ("Make it yours." panel).** It contains a Light spectrum select (3 palettes), Landscape height and Exhibit scale sliders, a Surface detail select (Automatic / Light / Balanced / Fine), Pause light, Hide interface, Walk in room, Motion look, Ambient sound, and a Gentle motion checkbox. Everything worked, and the `aria-pressed` state stayed in sync (the ambient-sound state was mirrored in the top-bar speaker icon). The height slider at 1.80× visibly stretched the relief.
5. **Palette button on the toolbar.** It switched Aurora (teal/coral) → Nebula (violet/rose); the room lighting and rings recoloured along with the relief (screenshot 06).
6. **Destinations (› button): Seahorse valley (77.78×), Elephant valley (63.64×), The little universe (100×).** Each one animates and updates the caption and zoom readout. In these zoomed views the relief is a square slab overhanging the round pedestal, and large flat dark "inside the set" plateaus take up half or more of it (screenshot 02).
7. **Drag to orbit, then scroll to approach.** Both were smooth and responsive. Low orbit angles let you look at the relief edge-on, where it reads as a curtain.
8. **Double-clicked the landscape to dive, then used the zoom-in/zoom-out buttons.** The dive re-centred on the clicked point and switched the destination to "Your discovery" (2.40×). Zoom-in went to 4.00× and zoom-out back to 2.40×. The relief recomputes quickly (screenshot 03).
9. **Slow-orbit toggle and Home.** The toggle worked. Home resets the destination but **does not leave Walk mode**; I had to use "Orbit exhibit" in the panel.
10. **Help (?) guide.** A well-written modal covering touch, mouse, keyboard (WASD/arrows, R, H, Esc) and headset controls, the formula, an honest note that this is "an escape-time relief, not a Mandelbulb", and HTTPS advice. Esc closes it.
11. **XR info.** A "Step inside." sheet: "No immersive WebXR session is available here. Explore the room in screen view." It has a table listing the interactive 3D room as Available, Immersive VR and AR as Unavailable here, and the connection as Secure, plus headset guidance (Quest/PICO; Steam Frame depends on the browser; iPhone gets touch/motion view). There is no dead Enter VR button. A hidden "Enter AR" button exists in the DOM for supporting devices (screenshot 04).
12. **Keyboard.** After clicking toolbar buttons, H and R did nothing because a focused button swallows them. After clicking the canvas, H hid the UI (leaving a "Show controls" pill) and R returned home. Holding W (synthetic keydown held 1.5 s) walked the camera into the room. Single taps barely move it, which is expected for hold-to-move.
13. **Phone layout (390×844 window → 446×741 CSS viewport).** The layout adapts cleanly: the top bar is reduced to Help + XR info, the toolbar is compacted (prev/next, palette, orbit, home, controls), and there is no horizontal overflow. The controls panel becomes a scrollable sheet that fits the screen (screenshot 05). Walk mode on this (non-touch) desktop showed no movement pad, since that seems tied to coarse pointers, so I couldn't verify it. The hint line still says "Double-click / Scroll" because the pointer isn't coarse.
14. **Restored the window to 1203×928 and closed the tab.** The console was still empty at the end.

## Overall score: 8 / 10

## Top 5 issues

1. **Major: zoomed destinations are dominated by flat interior slabs.** Evidence: screenshots 02 and 03. Seahorse/Elephant valley show half the square relief as a raised, flat dark plateau, and the square slab visibly overhangs the round pedestal. The best boundary detail is lost under blocky terraces. *Fix:* render the interior low (or as a recessed glossy pool) rather than at maximum height, and use smooth/continuous escape-time (normalised iteration count) to remove the stair-stepping. Clip or fade the relief to a disc that matches the pedestal.
2. **Minor/major: unexplained startup frame rate of ~2–3 fps in the first session.** Evidence: rAF timing showed 1.7–3.0 fps with 600–900 ms frames in a visible, focused tab; later reloads held 60 fps. *Fix:* if relief generation or shader compilation runs on the main thread at startup, chunk it or move it to a worker, show a progress state, and make sure "Automatic" quality backs off on slow frames rather than staying stuck.
3. **Minor: keyboard shortcuts stop working whenever a UI button has focus.** Evidence: H and R had no effect after clicking a toolbar button or XR info; they worked only after clicking the canvas. *Fix:* handle shortcuts at the `window` level, ignoring them only for text inputs and selects, or blur buttons after pointer clicks.
4. **Minor: Home / R doesn't exit Walk mode, and the hero copy is permanent in orbit mode.** Evidence: after walking, Home reset the destination but kept the first-person camera. The large "The infinite room." block stays over the left third of the scene until you switch to walk mode or press H. *Fix:* make Home restore orbit mode too, and fade the hero copy after the first interaction or a few seconds.
5. **Minor: the XR info status colours and touch hints aren't differentiated.** Evidence: "Unavailable here" uses the same teal accent as "Available". The hint line uses mouse wording; the movement pad couldn't be checked without a coarse pointer. *Fix:* use a muted or amber colour for unavailable rows, and pick hint wording from `(any-pointer: coarse)` / touch events, not just the primary pointer.

## Strengths

1. Zero console errors or warnings, and truly standalone (no network fetches). It was a steady 60 fps on every quality tier once running.
2. Excellent XR-unsupported handling: no dead buttons, a clear per-capability table, HTTPS guidance and per-device notes.
3. Strong, cohesive art direction: an observatory room, curved typography, glowing rings, and palettes that recolour the whole room, not just the fractal.
4. A rich, well-labelled control set: destinations, double-click dive, zoom, palettes, height/scale sliders, quality tiers, walk mode, motion look, ambient sound, gentle-motion accessibility option and a hide-UI mode. `aria-pressed` states stay in sync.
5. A thoughtful onboarding guide that covers touch, mouse, keyboard and headset input (teleport, 30° snap turn, grip-to-summon panel, gaze dwell for no-controller devices), and is honest about what the visualisation is.

## Verdict

A polished, error-free and well-thought-out "Mandelbrot observatory" with standout UX, accessibility touches and exemplary messaging when XR is unavailable. The main weakness is the fractal itself: the stepped escape-time relief with raised flat interiors turns the zoomed destinations into blocky slabs, which caps the wow factor. An early, unreproduced low-fps spell is also worth a look.
