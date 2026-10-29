# Browser Review — candidate-05

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Loads & renders | 7 | Loads instantly with no console errors; a styled landing page and an animated WebGL backdrop appear within about 1 s. |
| 2. Done-when (desktop-checkable) | 3 | The 3D scene is mostly glowing wavy "ribbon" walls. The Mandelbrot set shows up only as a faint, sparse purple speckle cloud that is barely visible. |
| 3. Visual wow effect | 4 | The neon-tube aesthetic and typography look good, but the fractal, which is the subject, is nearly invisible: no colour bands, no glow, no recognisable cardioid. |
| 4. Usability & controls | 4 | There is one button. Drag-orbit works, wheel zoom has no visible effect, and there are no keys, presets or palettes. The overlay can't be hidden and covers the left third of the scene. |
| 5. Robustness | 6 | There are no JS errors and the phone layout reflows cleanly. rAF ran at about 2 fps here, which is probably partly the test environment (inconclusive). |
| 6. XR readiness & messaging | 4 | The button is labelled "Launch 3D room", not "Enter VR". On unsupported devices it still calls requestSession and fails. The fallback message points to a "3D touch view" that doesn't exist as a separate control. |

## Steps performed

1. **Opened a new tab at http://localhost:8705/ and stubbed alert/confirm/prompt.** Title "MANDELBROT // LUMEN ROOM". `navigator.xr` exists. The page initialised at once. The "INITIALIZING FRACTAL FIELD" loader had already faded out (`#loading.done`).
2. **Took a landing screenshot** (`screenshots/01-landing.jpg`). It shows a large gradient title "THE MANDELBROT SET", a tagline, a "LAUNCH 3D ROOM" button with the hint "DRAG TO ORBIT · PINCH TO ZOOM", and a bottom-right hint block (VR / AR / ESC). Behind it is a full-screen canvas of glowing cyan sine-wave tubes with a horizon glow band.
3. **Read the console after reload.** It was empty: no errors and no warnings at load.
4. **Inspected the DOM.** It has one canvas (`#gl`, WebGL1 context), an 8.3 KB inline script, one visible button `#enter`, and a hidden `#ar` "View in AR" button (`class="hide"`, because AR isn't supported). The only interactive element the accessibility tree reports is "Launch 3D room".
5. **Clicked "LAUNCH 3D ROOM"** (three times over the session). Each click logged a console **warning** `NotSupportedError: The specified session configuration is not supported.` (from line 130). The status text changed to "XR COULD NOT START — TRY THE 3D TOUCH VIEW" (`screenshots/02-after-launch-xr-failed.jpg`). No native dialogs appeared. Nothing else changed: no separate touch view opened, and the overlay stayed in place.
6. **Dragged on the canvas** horizontally and vertically. Orbit works: the ribbons bend into concentric ellipses (side view) or horizontal bands (top view). Viewed from above, a very faint purple/indigo point speckle in roughly a Mandelbrot silhouette is visible in the centre (`screenshots/03-topdown-orbit.jpg`, zoomed in `04-topdown-zoom-faint-mandelbrot.png`). It is only recognisable when you zoom into the screenshot.
7. **Mouse wheel**, 15 ticks up and then 20 down. There was no visible zoom change in the scene.
8. **Keyboard** (W×6, arrow keys, Space, P, 1, 2, Esc after clicking the canvas). Nothing visibly changed. Keyboard navigation isn't offered and isn't advertised, apart from "ESC: return to the portal".
9. **Checked XR support.** `isSessionSupported('immersive-vr')` = false and `('immersive-ar')` = false. No WebXR emulator is installed. The page still shows the main button enabled and lets it attempt a session.
10. **Measured frame rate.** rAF ran at about 2.0 fps (600 ms per frame), with the hardware GPU (ANGLE / RX 6650 XT). The main thread was idle (max setTimeout gap 5 ms). A separate tiny WebGL readback returned in under 5 ms, and hiding the canvas didn't restore rAF (2.5 fps). That points to environment throttling of rAF in this automated window rather than proven GPU overload, so I count it as **inconclusive**. Orbit drags still showed up in the screenshots.
11. **Phone layout.** `resize_window` to 390×844 had no effect (the tiling WM keeps the window size), so I embedded the same page in a 390×844 same-origin iframe instead (`screenshots/05-phone-390x844.png`). No horizontal overflow (scrollWidth 386). The title scales down, the bottom-right hint hides, and the button moves to the bottom where a thumb can reach it, with the hint text below. After tapping Launch, the status line "XR COULD NOT START — TRY THE 3D TOUCH VIEW" fits on one line (`06-phone-after-launch.png`). Drag-orbit also worked inside the phone frame.
12. **Cleanup.** Removed the iframe, re-read the console (only the three NotSupportedError warnings from step 5) and closed the tab.

## Overall score: **4 / 10**

## Top 5 issues

1. **Critical: the Mandelbrot set is barely visible.** Evidence: `03-topdown-orbit.jpg` and `04-topdown-zoom-faint-mandelbrot.png`. The scene is dominated by decorative sine-wave tubes, and the fractal is a sparse, dark purple point speckle that only reads as a Mandelbrot when zoomed in from above. Fix: make the set the hero object. Render it as a dense, emissive height-field or point cloud with escape-time colour bands and bloom, put it at the centre of the room, and tone the ribbon walls down to an ambient backdrop.
2. **Major: there is no real "3D touch view" or non-XR room mode.** Evidence: step 5. After XR fails, the status tells the user to "try the 3D touch view", but no control for it exists. The landing overlay (title, paragraph, hint) stays on screen and covers the scene permanently. Fix: on unsupported devices make the button open an inline fullscreen 3D mode that hides the hero copy and offers a back button, and update the message to match.
3. **Major: XR entry ignores `isSessionSupported`.** Evidence: steps 5 and 9. VR is reported unsupported, yet the primary button still calls `requestSession`, and each click logs a NotSupportedError warning. The button never says "Enter VR". Fix: check support up front. Label the button "Enter VR" or "Enter AR" when supported and "Explore in 3D" otherwise, and say plainly "No VR headset detected" instead of failing after the click.
4. **Major: controls are minimal and partly non-functional.** Evidence: steps 7–8. Wheel zoom did nothing visible on desktop (the hint advertises pinch-to-zoom). There are no presets, palettes, iteration or detail controls, no reset view, and no keyboard navigation. Fix: wire the wheel to camera distance, add a small control panel (palette, iterations, auto-rotate, reset), and add WASD or arrow movement inside the room.
5. **Minor: frame-rate risk and the WebGL1 context.** Evidence: step 10. About 2 fps was measured here, probably environment-throttled, but nothing in the page adapts quality (no dynamic resolution, DPR cap or FPS readout). Fix: cap the render scale, add adaptive resolution, and prefer WebGL2. Standalone headsets need a stable 72–90 fps.

## Strengths

- Clean, fast load with zero JS errors at startup and no native dialogs. Failure states go to an inline status line.
- The landing page is polished: a strong gradient display title, tasteful monospace copy and a coherent neon palette.
- The responsive layout works well at phone width: no overflow, the hint hides, and the button moves within thumb reach.
- Drag-orbit responds on both mouse and the phone-sized frame, and the animated ribbon field has a pleasant, hypnotic motion.
- The AR button is correctly hidden when `immersive-ar` isn't supported, so an affordance that would fail isn't offered.

## Verdict

The page makes a stylish first impression, but the Mandelbrot set it is about is almost invisible: decorative glowing ribbons dominate the 3D scene, and the fractal is a faint speckle. On desktop without XR, the only button fails with a message that points to a "3D touch view" that doesn't exist. The task's core "wow" and done-when requirements aren't convincingly met from what is observable here.
