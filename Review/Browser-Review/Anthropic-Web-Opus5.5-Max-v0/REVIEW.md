# Browser Review — candidate-07

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Loads & renders | 9 | Fully self-contained (~666 KB, no network requests), DOMContentLoaded at 144 ms, the 3D room is visible behind the intro card right away, and the console stays empty. |
| 2. Done-when (desktop-checkable) | 9 | A real room (walls, floor, light strips, wall screen, info boards) holds a plinth with a 3D Mandelbrot height-field. The VR, AR, Cardboard and look-around entry paths are built in and gated sensibly. |
| 3. Visual wow | 8 | The plateau landscape with banded palettes, a wall screen mirroring the 2D view with a frame for the plinth area, and a guided tour all look good. Crater/Distance shapes at depth get jagged and spiky. |
| 4. Usability & controls | 7 | Drag/tap/right-click/wheel/keys all work, there are 44 px touch targets, and the in-room help boards are good. Orbit is very sensitive, the camera can end up behind the panel, and blind zooms land in featureless areas. |
| 5. Robustness | 8 | No errors or unhandled rejections through about 40 interactions. Window resizing was impossible here and frame rate couldn't be measured because the browser was throttling. |
| 6. XR readiness & messaging | 9 | XR buttons appear only when `isSessionSupported` is true, and the status line says plainly that no runtime answered. It requests local-floor and hand-tracking, and the in-world tablet and controls board cover headset use. |

**Test environment note:** The Chrome window was fixed at 446×763 CSS px by the window manager, and `resize_window` had no effect (tried 1366×860 and 390×844). The whole test therefore ran at a phone-like width; a wide desktop layout couldn't be checked. Chrome throttled requestAnimationFrame to exactly one frame every 600 ms, with zero long tasks, on a real GPU (RX 6650 XT through ANGLE). Low frame rates seen here come from the environment, not the page.

## Steps performed
1. **Loaded http://localhost:8707/ and stubbed the native dialogs.** The page initialised in about 150 ms. Behind a glass intro card ("Mandelbrot room", z ↦ z² + c) the 3D room and plinth landscape were already rendering. → OK
2. **Console and error check.** I reloaded with console tracking on and hooked `error`/`unhandledrejection`. There were 0 console messages and 0 errors, both at load and at the end of the session. → OK
3. **Introspection.** `navigator.xr` exists. `isSessionSupported('immersive-vr' / 'immersive-ar')` both return false, and secure context is true. There are two inline scripts (~578 KB library and ~79 KB app), no external resources, and one canvas. → Truly standalone and works offline.
4. **Intro card.** Only "Explore on screen" is visible. "Enter VR", "Enter AR", "Look around" and "Phone headset" are hidden. The status line reads "WebXR is present, but no headset or AR runtime answered. Explore on screen or use a phone mode." The "How to use it" disclosure covers headset, screen, phone-headset and key bindings. → Clear, though "use a phone mode" points at buttons that are hidden on desktop.
5. **"Explore on screen".** The HUD appears (centre coordinate, width, iterations, render progress), along with a bottom toolbar: Zoom out / Back / Tour / Shape / Colours / Flow colours / Menu. → OK (screenshot 02)
6. **Drag to orbit.** It works, but it is very sensitive (a 100 px drag turned the camera by more than 90°) and has inertia. Once the camera ended up at plinth height looking through the in-world tablet, which filled the foreground as a black slab. Dragging vertically tilts to a pleasant top-down view. → Works, needs smoothing and clamping.
7. **Mouse wheel.** It dollies the camera back a little. This isn't mentioned in the help. → OK
8. **Click to zoom.** A white rectangle previews the target area. Each click zooms 2× around the clicked point, and iterations scale automatically (180 → 206 → 315 → 471). Rendering is progressive ("Rendering N %"). → OK
9. **Back button and Backspace.** Both restore the previous view correctly (width 0.4 → 0.2). The progressive render restarts from 0 % with no cache. → OK
10. **Right-click.** It zooms out (0.2 → 0.4) with no context menu. In one case a "-" key press followed right away by a right-click produced only one zoom-out step. → Minor
11. **Shape button and `s` key.** They cycle Plateau → Crater → Distance. Crater and Distance at deep zoom show tall jagged "walls" with spiky aliasing. → Works, but less attractive.
12. **Colours button and `c` key.** They cycle Classic → Ember → Lagoon. "Flow colours" toggles an animated palette cycle; its label changes to "Hold colours" and the button turns highlighted. → OK
13. **Tour (`t` key).** It flies into "Seahorse valley" (the HUD shows "Tour: Seahorse valley"), zooming steadily from width 1.6 to 0.1. Pressing `t` again stops it. → OK (screenshot 03)
14. **`]` detail key.** Accepted, with no visible confirmation in the HUD. → Unclear feedback
15. **Menu.** It returns to the intro card, and "Explore on screen" resumes with state kept. → OK
16. **Zoom out button ×4.** Returns to width 3.20, but keeps the off-centre coordinate (-0.7392 + 0.1277i) instead of recentering. → Minor
17. **In-room content.** Orbiting showed a "z ↦ z² + c" explainer board, a "Controls" board for headsets (trigger/pinch zooms, grip zooms out, trigger on the wall teleports, sticks walk/turn/raise the landscape), and a floating tablet next to the plinth with buttons. → Strong XR affordances (screenshot 04)
18. **Five quick clicks on the landscape.** The zoom drifted from the boundary into a plain gradient region (width 0.1) with no structure and no hint about how to get back. → Minor usability
19. **Phone layout (446×763, the actual viewport).** The intro card fits and scrolls. The toolbar scrolls horizontally inside a pill (scrollWidth 759 vs 420), with only a clipped button hinting at the overflow. All toolbar buttons are 44 px tall. The HUD fits. Resizing to 390×844 or to a desktop size was not possible (see note). → Good
20. **Frame-rate sampling.** 1.8 fps measured, with rAF gaps of exactly 600 ms and 0 long tasks, so this is environment throttling, not a page bottleneck. → Not assessable
21. **Closed my tab.**

## Overall score: 8 / 10

## Top 5 issues
1. **Major — orbit camera sensitivity and occlusion.** In step 6, a short drag spun the view by more than 90° and left the camera low, with the in-world tablet blocking the view as a black slab. *Fix:* lower the rotate speed and damping, clamp the polar angle and the minimum distance, and hide or fade the tablet in screen mode (or keep it out of the orbit sightline).
2. **Minor — "use a phone mode" message on a device with no phone modes.** The desktop status text recommends phone modes, but those buttons are hidden. *Fix:* adjust the copy per device ("Explore on screen; open on a headset or phone for immersive modes").
3. **Minor — Crater/Distance shapes at depth look jagged.** In steps 11 and 13, vertical walls with spiky aliasing appear at the boundary. *Fix:* clamp or smooth the height gradients (cap the slope, use a smooth iteration count for height, or add a mipmapped normal), and possibly lower the vertical exaggeration in those modes.
4. **Minor — getting lost when zooming.** In step 18, clicks can wander into featureless regions with no structure. Zoom out also keeps the off-centre coordinate (step 16). *Fix:* add a "Reset view" or "Home" button, and/or snap or suggest nearby boundary detail; recenter when zooming fully out.
5. **Minor — feedback and discoverability.** The `[`/`]` detail keys give no HUD feedback. The toolbar overflow on narrow screens is only hinted at by a clipped button. Back re-renders from 0 % instead of reusing the cached previous view. *Fix:* flash "Detail: N" in the HUD, add an edge fade or arrow on the scrollable toolbar, and cache the last few height-field textures for Back.

## Strengths
- Fully standalone single file (library inlined, zero network requests). It loads in about 150 ms with a clean console and no runtime errors in the whole session.
- Real "virtual room" staging: walls, light strips, a big wall screen mirroring the 2D view with a frame for the plinth area, explainer and controls boards, and an in-world tablet UI for headset use.
- Well-designed XR gating: VR/AR buttons appear only when `isSessionSupported` is true, an honest status message is shown, and it requests local-floor plus optional hand-tracking. Look-around and Cardboard-style "Phone headset" fallbacks cover phones without WebXR (e.g. iOS Safari).
- A rich explorer: point-to-zoom with a target preview, a Back history, a guided Tour, three height shapes, three palettes plus animated colour flow, auto-scaling iterations, and keyboard shortcuts.
- Phone-friendly UI: 44 px touch targets, a scrollable toolbar pill, a compact HUD, and a readable glass intro card at about 450 px wide.

## Verdict
A polished, truly self-contained WebXR Mandelbrot room that meets the brief: a real 3D height-field set in a furnished room, with sensibly gated VR/AR entry and phone fallbacks, and no errors at all. The main weaknesses are a twitchy orbit camera that can end up behind the in-world tablet, and rough geometry in the Crater/Distance shapes at deep zoom. Neither blocks the core experience.

Screenshots: `screenshots/01-intro-panel.jpg`, `screenshots/02-explore-start.jpg`, `screenshots/03-tour-crater-seahorse.jpg`, `screenshots/04-room-controls-panel.jpg`
