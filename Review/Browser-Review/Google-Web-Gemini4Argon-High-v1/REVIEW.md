# Browser Review — candidate-08

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Loads & renders | 9 | DOMContentLoaded about 160 ms. The 3D scene was up within the first screenshot, with no errors (only the Tailwind-CDN warning). |
| 2. Done-when (desktop-checkable) | 8 | A real 3D "room" with grid floor, pillars, rings and particles, a fractal pedestal and an in-scene 3D control slate. Prominent Enter VR / AR buttons. |
| 3. Visual wow effect | 8 | Mandelbulb mode and the top-down Auto-Dive are striking. Terrain and Cathedral modes are noisy, aliased spike fields. |
| 4. Usability & controls | 6 | Many controls and they work, but the Zoom buttons only act while held, a magenta ring keeps crossing the view, and the phone layout is cramped and overlapping. |
| 5. Robustness | 8 | No console errors during the whole session. After a warm-up dip (27→10 FPS) it held 60 FPS, including 1024 iterations and the Mandelbulb. Resizing was handled. |
| 6. XR readiness & messaging | 6 | VR and AR are offered and fail gracefully with a toast. But the buttons stay enabled even though the `isSessionSupported` checks return false, the toast is faint and short-lived, and the "Magic Window" gyro toggle reports "Active" on a desktop with no gyroscope. |

## Steps performed

1. **Opened a new tab at http://localhost:8708/ and stubbed alert, confirm and prompt.** The page loaded at once (DCL 162 ms). The first frame showed a dark sci-fi room: a perspective grid, cyan and yellow light pillars, magenta orbit rings, floating particles, a glowing pedestal with a Mandelbrot height-field, and a tilted in-scene "3D spatial UI" slate. The HUD showed Re, Im, Magnification and FPS. The console had only the Tailwind CDN "not for production" warning. Three.js r128 comes from cdnjs, `navigator.xr` exists, and there is one canvas.
2. **FPS readout.** It showed 27, then 15, then 10 FPS in the first seconds (likely shader warm-up), then stayed at 60 FPS for the rest of the session.
3. **Clicked "ENTER VR ROOM".** `isSessionSupported('immersive-vr')` is false here. A toast appeared: "IMMERSIVE-VR not supported on this device. Try a VR/AR headset or Magic Window." It is low-contrast and was already fading in a screenshot taken 2 s later. The button stays enabled and is styled as the primary call to action.
4. **Clicked "AR HOLOGRAM".** The same kind of toast appeared, for IMMERSIVE-AR. There were no native dialogs and nothing broke.
5. **Mode: Mandelbulb.** This showed a volumetric, ray-marched Mandelbulb with rich iridescent shading on the pedestal. It is the visual highlight and ran at 60 FPS (screenshot 02).
6. **Mode: Cathedral ("Room Canyon").** The camera ended up among large, jagged, aliased spikes on a flat green floor. It reads as visual noise rather than a recognisable fractal (screenshot 03).
7. **Presets in 3D Terrain mode.** Seahorse Valley (185×) and Elephant Valley (240×) flew there smoothly and updated the HUD coordinates, iterations and amplitude. The terrain is readable but has heavy high-frequency speckle on the spikes.
8. **Color palette.** Clicking cycled to "Inferno Gold" with a toast, and the change was visible.
9. **Fractal equation.** It toggles between Mandelbrot and "Julia Live Morph". At the Elephant Valley zoom, Julia mode turned the whole pedestal into a flat, featureless green and then magenta disc, so it looked broken there. At Full Overview it showed structure, but the palette choice was apparently ignored (neon colours while "Inferno Gold" was selected).
10. **Mouse orbit drag.** It orbits the room smoothly. Dragging the camera low gives an edge-on view where the terrain is hard to read.
11. **Mouse wheel over the pedestal.** It zooms the fractal (1.0× to 1.2× for 5 ticks).
12. **"＋ ZOOM" and "− OUT".** Single clicks left the magnification at 1.2× (checked three times). Only pointerdown followed by a 1.5 s hold changed it (1.2× to 8.6×). This hold-to-zoom behaviour is not labelled.
13. **D-pad arrows.** They pan the fractal (Re and Im change).
14. **Keyboard.** "W" panned Im (0.30 to 0.94). "E" and "+" did nothing visible. No keyboard help is shown.
15. **Orbit/Pan toggle.** Switching to "Pan" makes a drag pan the fractal, with a toast "1-Finger Drag: Fractal Coordinates Pan". It works.
16. **RST.** It reset the coordinates but not the camera, so the view stayed edge-on.
17. **Auto-Dive.** It zooms continuously into Seahorse Valley, reaching about 8e4× in roughly 15 s with crisp detail and changing colours (screenshot 04, from top-down). It then loops back to a low zoom. It is the best "wow" moment in Terrain mode, but a magenta orbit ring keeps passing in front of the fractal.
18. **Sliders.** Iterations at 1024 and Power/Morph at 3.5 both updated live, and the Mandelbulb morphed visibly while holding 60 FPS.
19. **Gyro (compass) button.** The toast said "Mobile Gyroscope Look-Around Active" on a desktop that has no gyroscope.
20. **Audio button.** "Harmonic Fractal Telemetry Audio Enabled", then "Audio Muted". It works as a toggle.
21. **Hide UI / Show UI.** It hides the deck and the D-pad. It works.
22. **Resized to 390×844 (inner viewport 446×741).** There is no horizontal scroll. The "Hologram Synthesis Deck" covers about 70% of the screen and scrolls internally. The Re/Im/Zoom HUD text sits underneath and behind the button row (it collides with "ENTER VR ROOM"), and the toast overlaps the buttons. With Hide UI the fractal fills the screen, which looks good, though blocky per-texel aliasing is visible (screenshots 05 and 06).
23. **Restored the window and reloaded.** The scene re-laid out correctly. The console was clean apart from the Tailwind warning, and no ALERT, CONFIRM or PROMPT messages appeared.
24. **Closed the tab.**

Screenshots are in `screenshots/`: 01-initial-terrain, 02-mandelbulb, 03-cathedral, 04-autodive-topdown, 05-phone-deck, 06-phone-hidden-ui.

## Overall score: 7 / 10

## Top 5 issues

1. **Major: the Zoom buttons do nothing on a normal click.** In step 12, magnification stayed at 1.2× after three clicks and only changed under a 1.5 s pointer hold. *Fix:* apply a discrete zoom step (for example ×1.5) on click and keep continuous zoom while held, or label the buttons "hold".
2. **Major: Terrain and Cathedral height-fields are noisy and aliased.** Speckled, single-texel spikes undercut the wow effect in the default mode (screenshots 01 and 03), and the Cathedral camera lands in a jumble of jagged spikes. *Fix:* smooth or low-pass the height map (continuous escape-time with a log-log term, height clamped near the boundary), add mip filtering or supersampling, and frame the Cathedral camera on a readable vista.
3. **Major: the phone layout is cramped and overlapping.** At 446×741 the deck covers most of the screen, the HUD coordinate row collides with the "ENTER VR ROOM" button row, and toasts overlap the buttons (screenshot 05). *Fix:* on small screens, collapse the deck into a bottom sheet that starts closed, hide or move the coordinate HUD, and put toasts below the toolbar.
4. **Minor: XR availability is not reflected in the UI.** Both `isSessionSupported` checks return false, yet the VR and AR buttons look fully enabled. The failure toast is faint and fades within about 2 s. The "Magic Window" fallback it mentions is a hidden compass icon, which reports "Active" even with no gyroscope. *Fix:* check support at load, show an inline "VR not available on this device" state on the buttons, make the toast persist until dismissed, and only offer the gyro toggle when `DeviceOrientationEvent` data actually arrives.
5. **Minor: assorted state and visual glitches.** Julia mode at deep presets renders a flat, single-colour disc, and Julia ignores the selected palette. RST does not reset the camera. A magenta orbit ring sweeps through the fractal view. Icon-only buttons have only `title`, no `aria-label`. Tailwind is loaded from the Play CDN, which logs a production warning and needs a network connection. *Fix:* clamp or adjust the Julia c and zoom, make RST also reset the camera, route the ring around the fractal, add aria-labels, and inline the CSS.

## Strengths

1. The Mandelbulb mode is a genuinely impressive ray-marched volumetric fractal with rich shading, at a steady 60 FPS.
2. It is a coherent "virtual room": grid floor, light pillars, particles, a pedestal, and an in-world 3D control slate meant for XR laser interaction.
3. Auto-Dive and the famous-location presets give smooth fly-to animation with a live coordinate and magnification HUD, and Auto-Dive reaches about 1e5× with crisp detail.
4. Rich, working controls: three modes, six presets, palettes, a Julia toggle, iteration, amplitude and power sliders, an Orbit/Pan toggle, a D-pad, wheel zoom, audio, and Hide UI.
5. Robust: no console errors, no native dialogs, fast load, and resizing is handled cleanly.

## Verdict

This is a polished, visually ambitious WebXR fractal room. The Mandelbulb and Auto-Dive views deliver real wow, and the page has a clear, gracefully failing path into VR and AR. The default terrain rendering is noisy and aliased. The Zoom buttons, phone layout and XR-availability messaging need work before it feels smooth on phones and for users who expect the buttons to respond to a click.
