# Browser Review — candidate-06

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Loads & renders | 9 | Load event at ~136 ms, 3D room and relief visible at first screenshot; zero console messages across every session. |
| 2. Done-when (desktop-checkable) | 8 | A real gallery room around a 3D Mandelbrot relief on a plinth; the XR path is present but correctly disabled here. It deliberately does not use three.xr.js, and says why. |
| 3. Visual wow | 8 | Polished "observatory" look: plinth, glass case, wall plaques, halo ring, three palettes. Zoomed presets look weaker (thin floating slab). |
| 4. Usability & controls | 8 | Orbit, scroll, walk mode with WASD and an on-screen pad, minimap click-to-center, presets, palettes, detail and relief controls, plus a thorough guide. On narrow screens the Explore panel hides the view, and the header icons are 34 px. |
| 5. Robustness | 8 | No errors. Unavailable fullscreen and motion sensors are handled with clear toasts, and stereo exits cleanly. Frame rate could not be measured in this environment (see notes). |
| 6. XR readiness & messaging | 8 | `isSessionSupported` gating; "VR unavailable here" is a disabled button with a plain explanation. AR (room and tabletop) is hidden when unsupported. Split-screen stereo and a gyro fallback are offered. Untestable without a device. |

**Overall score: 8 / 10**

## Environment notes
- The Chrome window is managed by a tiling WM. `resize_window` to 1280×800 and to 390×844 had no effect, and the viewport stayed **446×763** (already phone-like). I checked the wide desktop layout and an exact 390×844 layout by putting the same URL into a scaled iframe overlay.
- `navigator.xr` exists, but `isSessionSupported('immersive-vr'|'immersive-ar')` both return `false`. No WebXR emulator is installed.
- `requestAnimationFrame` ran at about 1.8 fps, with the canvas shown or hidden alike. The main thread was idle: 498 `setTimeout(0)` ticks in 2 s and no long tasks. A separate WebGL context did `readPixels` in under 1 ms, so the GPU was not saturated. I attribute this to rAF throttling of the window in this environment, not to the page. **Real frame rate is unverified.** Interactions were reflected promptly in screenshots.

## Steps performed
1. **Opened the page in a new tab and installed the dialog shims.** Title "Mandelbrot Observatory · A room for infinity". It shows a full-screen gallery room with a teal/cream Mandelbrot relief on a black plinth inside a glass case, wall plaques ("SIMPLE RULES. ENDLESS POSSIBILITY.", "MANDELBROT OBSERVATORY"), and a bottom nav (Walk inside / Recenter / Motion / Explore). (`screenshots/01-initial-full-set.jpg`)
2. **Reloaded and read the console.** No messages at all: no errors, no warnings, and no native dialogs, so the shims never fired. The page is one inline script of about 600 KB with Three.js r186 bundled, and makes no CDN requests.
3. **Opened the Guide (?).** A long, accurate field guide covering the equation, what the height encodes, the controls, file/HTTPS caveats for XR, device support (Quest/PICO/Steam Frame/Android AR/iOS fallback), and why three.xr.js was replaced by the native WebXRManager. It closes with ×.
4. **Opened the Explore panel.** It has a Destination select (Full set / Seahorse valley / Elephant valley / The satellite), palettes (Aurora / Ember / Violet), a Relief height slider, Detail (Light 192 / Balanced 320 / Fine 640 iterations), a magnification and iteration readout, a clickable complex-plane minimap, − / Reset set / +, and the XR button.
5. **Selected the Ember palette.** The minimap and the 3D relief recoloured.
6. **Clicked the minimap near the seahorse area, then + three times.** Magnification went to 4.9× and the minimap updated. Closing the panel showed the relief regenerated (`02-zoom-4.9x-ember.jpg`). The "+" glyph briefly vanished after repeated clicks, a cosmetic pressed-state glitch.
7. **Set the Seahorse valley preset, dragged to orbit, and scrolled to zoom.** Both work. The zoomed relief reads as a thin floating slab of cream plateau with orange stalactites, hovering well above the teal plinth surface (`03-seahorse-floating-slab.jpg`).
8. **Recenter.** The camera returns and a "View centered." toast appears.
9. **Walk inside.** Switches to a first-person view with a crosshair and a MOVE joystick, and the button becomes "Orbit exhibit". `S` ×30 walked backwards, drag looked around, and the joystick drag moved forward.
10. **Motion on desktop.** Shows "Hold your phone upright…". After a few seconds without sensor data it switches itself off with "No motion readings arrived. Try HTTPS and allow motion sensors, or use touch." Good fallback.
11. **Fullscreen button.** A `fullscreenerror` fired (this WM). The page showed the toast "Fullscreen is unavailable in this browser. The room still works in this view." Handled cleanly.
12. **Guide → "Start split-screen stereo".** Side-by-side stereo with an "Exit stereo" pill and the hint "Landscape view works best. This mode has no lens-distortion correction." Escape exits (`04-split-stereo.jpg`).
13. **XR buttons.** `#enter-vr` reads "VR unavailable here", is `disabled`, and has the note "No immersive session is available in this browser. The interactive room still works." `#enter-ar` and `#enter-ar-mini` ("Enter AR · full-size room" / "tabletop exhibit") are hidden. A "Leave XR" button, a "Place gallery here" button and an in-world panel exist for real sessions but could not be exercised.
14. **Desktop 1280×800 (scaled iframe).** Proper desktop layout: the headline block on the left with the equation, the Explore side panel docked on the right, a bottom toolbar, "Drag to orbit · scroll to move closer" and a coordinate readout (`05-desktop-1280x800-iframe.png`).
15. **Phone 390×844 (iframe).** No horizontal scroll (scrollWidth 390). Bottom nav buttons are 87×43 px, but the Help and Fullscreen icons are only 34×34 px.
16. **Fresh reload, then Violet palette, Fine detail, relief 1.35×, orbit.** Regenerated within about 3 s with the richest look of the session (`06-violet-fine.jpg`). The console stayed empty.
17. **Closed the tab.**

## Top 5 issues
1. **Major: zoomed destinations look much less convincing than the full set.** At 4.9× and at Seahorse valley, the relief becomes a flat cream plateau slab with fringe spikes, floating above an empty teal plinth (`02`, `03`). The 3D "wow" mostly disappears once you explore. *Fix:* renormalise height per view (percentile-based min/max of the smooth escape count), anchor the lowest sample to the plinth surface, and colour the base by escape value so the plinth isn't a flat teal slab.
2. **Major (unverifiable here): real frame rate is unknown.** rAF ran at about 1.8 fps in this environment, very likely due to throttling rather than the page (idle main thread, idle GPU). The scene still has two canvases, a glass case, a halo ring and an up to 288×216 mesh. *Fix:* verify on a Quest or a mid-range phone, and add an adaptive-quality fallback (auto-drop to Light, limit pixel ratio) when frame times exceed budget.
3. **Minor: the HTML headline permanently overlays the 3D scene on narrow screens.** "A room for infinity." collides with the in-scene halo ring and the wall plaques ("SIMPLE RULES" text under the headline in `06`), and takes about a quarter of the phone viewport. *Fix:* fade or collapse the hero text after first interaction or in walk mode, or give it a dismiss affordance.
4. **Minor: on phone widths the Explore panel covers almost the whole view.** Palette, relief and zoom changes can't be seen live until the panel is closed. *Fix:* use a half-height bottom sheet on narrow viewports, or make the panel translucent or draggable so the exhibit stays visible.
5. **Minor: small touch targets and a cosmetic glitch.** The header Help and Fullscreen buttons are 34×34 px, below the 44 px guideline. The "+" zoom label briefly disappeared after rapid clicks. *Fix:* enlarge the hit areas to at least 44 px, and check the `:active`/pressed style of the zoom buttons.

(Spec deviation, informational: the brief asked for "three.xr.js". The page uses Three.js' built-in WebXRManager and states in the guide that the legacy library is archived and uses obsolete APIs. This is a defensible, transparent choice, but a strict grader may count it against the brief.)

## Strengths
- Fully self-contained: one inline bundle, no CDN, fonts or network. Fast load (~136 ms), and zero console output through every interaction.
- Real XR plumbing with careful gating: VR, AR full-room and AR tabletop entry points are shown only when supported, with honest disabled-state copy, plus Leave XR and placement flows and in-guide device notes for Quest, PICO, Steam Frame, Android and iOS.
- Graceful fallbacks everywhere: gyro "Motion" mode with auto-timeout messaging, split-screen stereo for simple viewers, and a handled fullscreen failure. None of them use native dialogs; all messages are inline toasts.
- Rich, sensible controls: orbit and first-person walk (WASD plus an on-screen joystick), minimap click-to-center with ± zoom, presets, palettes, relief height and detail levels. Layouts work at desktop and phone widths.
- High production value: a cohesive gallery aesthetic and typography, and an excellent explanatory guide that is honest about what the 3D height encodes.

## Verdict
This is a polished, self-contained Mandelbrot "observatory": a real 3D room, clean code health (no console errors), and careful, well-communicated XR, motion and stereo fallbacks. Its main weakness is that zoomed regions render as an unconvincing floating slab, and real-device frame rate could not be verified here. It also intentionally swaps three.xr.js for native WebXR. On desktop evidence it is one of the more complete deliveries.
