# Browser Review — candidate-03

| Criterion | Score | Reason |
|---|---|---|
| 1. Loads & renders | 8 | Renders a full scene within ~3 s; zero console errors or warnings across several reloads. |
| 2. Done-when (desktop-checkable) | 5 | There is a room with a 3D Mandelbrot heightfield, but on this desktop there is no visible path into XR, and the set itself is hard to recognise. |
| 3. Visual wow effect | 5 | The neon grid floor, light shafts, glowing pedestal and halo ring make a strong stage. The fractal is a washed-out cream slab with noisy spikes, and from above the set's interior shows as a hole. |
| 4. Usability & controls | 4 | Drag and wheel work. Drag tumbles the object and can flip the view into the pedestal or the sky, the in-world help panel is mirrored, keyboard does nothing, and there are no presets or palettes. |
| 5. Robustness | 6 | Steady 60 fps, the canvas follows window resizes, no errors. The fractal plane clips through the pedestal, and the scene drifts on its own into odd angles. |
| 6. XR readiness & messaging | 4 | The Enter VR/AR buttons exist in the DOM but are hidden when unsupported, and nothing on screen says XR is unavailable. A static secure-context hint shows even on localhost. |

## Steps performed

1. **Opened http://localhost:8703/ in a new tab and waited 3–5 s.** Title: "Mandelverse — WebXR Mandelbrot Room". The scene shows a starfield room, a neon grid floor, vertical light shafts, a glowing cylindrical pedestal, a cyan halo ring that tilts and rotates, a flat cream plane with blue/orange spikes and a purple blob, and an in-world help panel. HTML overlay: the "MANDELVERSE" title, a "📱 Enable motion sensors" button, and a bottom hint box. (screenshot `01-initial-load-mirrored-panel.jpg`)
2. **Read the console after a reload, with tracking already active.** No messages at all: no errors, no warnings.
3. **JS introspection.** `navigator.xr` exists, `isSecureContext` is true, and `isSessionSupported('immersive-vr'/'immersive-ar')` both return false. The DOM holds `#btnVR` "🥽 Enter VR", `#btnAR` "🪟 Enter AR" and `#btnExit` "✕ Exit XR", all hidden. Only "Enable motion sensors" is visible.
4. **Read the in-world help panel.** The text is mirrored left-to-right, so the default desktop camera is looking at the panel's back. It lists Quest-style controller bindings (left stick move, right stick turn/zoom, trigger fly, squeeze/pinch grab, A/X reset).
5. **Read the bottom hint box.** It says "Drag = orbit · pinch / wheel = zoom · drag the fractal = move it · two-finger drag = pan · double-tap = reset", then "WebXR needs a secure context (HTTPS or localhost)…". That second line shows even though the page is already on a secure origin, and it never says why the VR/AR buttons are missing.
6. **Dragged on the fractal.** This moved the fractal off the pedestal, which matches "drag the fractal = move it".
7. **Double-clicked empty space.** The view reset correctly.
8. **Dragged vertically on empty space.**
   - Small drags (40–100 px) tilt the view, and dragging down gives a top-down look.
   - A 300 px upward drag left the screen solid pale blue: the camera or object ended up inside or against the pedestal.
   - A 150 px downward drag left the view pointing at the empty dark ceiling.
   - Pitch is not clamped well, so it is easy to lose the subject.
9. **Dragged horizontally on empty space.** The fractal plane tumbles while the floor stays put, so this behaves like object rotation rather than an orbiting camera. Afterwards the plane cut through the pedestal, with a shard sticking out below it. (screenshot `04-plane-clipping-pedestal.jpg`)
10. **Scrolled the wheel up 5 ticks.** It zooms in smoothly. The close-up shows a heightfield of spiky boundary "grass" around the set, and the set's interior renders as a hole you see the pedestal through (no fill or culling on the top side). There is no deep zoom into the fractal on desktop: the wheel only moves the camera closer. (screenshot `02-zoomed-top-view.jpg`)
11. **Pressed W ×20 and ArrowLeft ×10.** Nothing happened, so there is no keyboard navigation.
12. **Clicked "Enable motion sensors".** The button disappeared with no feedback on a desktop without sensors. No error.
13. **Measured performance.** Steady 60.0 fps via rAF over 3 s on an RX 6650 XT, dpr 1. The canvas renders at about 0.9× CSS size.
14. **Resized to phone width (390×844 requested; Chrome clamped it to a 446×741 viewport) and reloaded.**
    - No horizontal scroll, the overlay text wraps, and the motion-sensor button is 248×44 px, a fine touch target.
    - The hint box covers about 15% of the screen and never fades, even after 8 s.
    - The fractal is cropped at the sides and the help panel is still mirrored.
    (screenshot `03-phone-layout.jpg`)
15. **Restored a large window (1216×960 viewport).** The canvas resized correctly. The scene keeps drifting and tilting on its own between screenshots: the help panel moved out of view and the plane tilted into the pedestal.
16. **Closed the tab.**

## Overall score: 5 / 10

## Top 5 issues

1. **Major: Mandelbrot geometry is hard to read and partly broken.**
   - Evidence: `02-zoomed-top-view.jpg`. Most of the plane is a flat, unlit cream surface, the boundary is noisy spikes, and from above the set's interior is a hole that shows the pedestal. The purple interior only shows from low angles.
   - Fix: give the interior a solid, coloured cap (or render it double-sided), clamp and smooth the heights (log-smoothed iteration count), and apply a real colour palette to the escape region so the cardioid and bulbs read instantly.
2. **Major: no XR affordance or messaging when XR is unsupported.**
   - Evidence: `#btnVR`/`#btnAR` are hidden when `isSessionSupported` is false, and the only hint is a static secure-context line that is wrong on localhost.
   - Fix: always show the VR/AR buttons, disabled, with a reason ("No WebXR device detected — open on Quest/Pico/phone"). Show the HTTPS hint only when `!isSecureContext`.
3. **Major: in-world help panel faces away from the desktop/default viewpoint.**
   - Evidence: `01-initial-load-mirrored-panel.jpg`; the text is mirrored on both desktop and phone.
   - Fix: rotate the panel 180° or make it billboard toward the camera, and check that it faces the XR spawn pose too.
4. **Major: drag interaction loses the subject.**
   - Evidence: steps 8–9. Large vertical drags put the view inside the pedestal (solid blue) or at the ceiling, horizontal drags tumble the plane into the pedestal, and the scene keeps drifting by itself.
   - Fix: use a proper orbit camera with clamped polar angle and min/max distance, keep the fractal's pose fixed (or limit it to yaw), and keep it from intersecting the pedestal.
5. **Minor: thin desktop/phone feature set.**
   - Evidence: no keyboard controls, no presets, palettes or iteration controls, no fractal deep-zoom outside XR, a hint box that never auto-hides, and a motion-sensor button that vanishes with no feedback.
   - Fix: add a small settings panel (palette, height scale, preset locations), WASD/arrow keys, auto-fade the hint after the first interaction, and give feedback when motion sensors are unavailable.

## Strengths

- Clean load: no console errors or warnings, first frame in about 3 s.
- Strong atmosphere: neon grid floor, volumetric-looking light shafts, starfield, glowing pedestal and halo ring.
- Smooth 60 fps and correct canvas resizing at desktop and phone sizes.
- XR plumbing appears to be in place: VR, AR and Exit buttons exist, `isSessionSupported` is queried, and the controller bindings are written for Quest-style controllers and hand pinch.
- Phone layout has no horizontal overflow, readable text and a decent touch-target size.

## Verdict

The room and lighting are attractive and the page is technically clean. But the Mandelbrot itself is the weakest part of the scene: a pale slab with noisy spikes and a hollow interior, seen at first through a mirrored help panel. Desktop interaction easily loses the subject, and on a device without XR the page gives no visible path or explanation for entering VR/AR, so the done-when is only partly met on what can be checked here.
