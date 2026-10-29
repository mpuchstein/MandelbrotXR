# Browser Review — candidate-02

| Criterion | Score | Reason |
|---|---|---|
| 1. Loads & renders | 9 | Single inline script, FCP ≈ 68 ms on reload, a 3D scene is live behind the landing card at once, no console messages at all. |
| 2. Done-when (desktop-checkable) | 8 | A real room (starfield and nebula sky, grid floor, pillars, glowing rings) with a raised 3D Mandelbrot height field on a pedestal. A clear XR path exists in code (Enter VR/AR buttons), but they are hidden here, so I couldn't exercise that path. |
| 3. Visual wow | 8 | The holographic tabletop, palettes and live Julia inset are striking, and deep zoom (≈1e6×) holds detail. Spiky "grass" aliasing at the boundary, faceted interiors and terraced slabs in Immerse take some of the polish off. |
| 4. Usability & controls | 7 | Clear hint line, readable Re/Im/Zoom HUD, named locations ("Seahorse Valley"), and every button works. No keyboard navigation, Home doesn't reset the camera orbit, and the phone toolbar hides half its buttons behind a horizontal scroll with no affordance. |
| 5. Robustness | 8 | Zero console errors or warnings. Resizes cleanly with no page scroll. 60 fps across every mode on re-test, though one early session ran at ~2 fps that I couldn't reproduce. |
| 6. XR readiness & messaging | 7 | Feature-detects with `isSessionSupported` and hides VR/AR when they're unsupported. A plain-language note offers the browser fallback, and phone-only "Look around" and "Cardboard" modes exist in the DOM. The note says "no WebXR" even though `navigator.xr` exists (it's really "no XR device"). |

## Steps performed

1. **Opened my own tab, loaded `http://localhost:8702/`, waited 3 s, took a screenshot.** A landing card ("z ↦ z² + c / The Mandelbrot set as a place you can stand in") sits over a live 3D room: starfield and nebula sky, grid floor, pillars, and a fractal height field on a pedestal. Only "Explore in this browser" is shown, with the note "This browser has no WebXR, so VR and AR are unavailable. You can still explore it in the browser." (`01-landing.jpg`)
2. **Introspected with JS.** `navigator.xr` is present and the context is secure. `isSessionSupported('immersive-vr'/'immersive-ar')` both return false, and `#bVR`/`#bAR` exist with `display:none`. There's one canvas and one inline script. The WebGL renderer is the real GPU (ANGLE on AMD RX 6650 XT). Viewport meta includes `viewport-fit=cover`.
3. **Reloaded with console capture on.** No messages of any kind. FCP 68 ms, load event 87 ms.
4. **Clicked "Explore in this browser".** A HUD (Re/Im/Zoom) appears top-left, a "Julia set at the pointer" inset top-right, a hint line ("Click the landscape to dive in. Drag it to pan, scroll to zoom, drag the background to orbit."), and a bottom toolbar: Back, Zoom out, Home, Dive, Palette, Height, Immerse, Sound, Exit. The camera slowly auto-orbits. (`02-explore-tabletop.jpg`)
5. **Measured frame rate (first session).** About 2 fps (rAF every ~600 ms) with the main thread idle (max setTimeout gap 4 ms, no long tasks). It rose to ~17 fps at the 446×741 phone size. **Re-tested later, including after a fresh reload: a steady 60 fps** on the landing page, in explore, while diving, in Immerse, and with every palette and height. I couldn't reproduce the 2 fps phase, so it was probably a one-off warm-up or environment state, but it's worth noting.
6. **Clicked a ridge on the landscape.** It animated a dive: Zoom 1× → 3×, recentred to −0.5675 −0.3042i, and the Julia inset updated.
7. **Scrolled the mouse wheel up 5 ticks.** Zoom went 3× → 5.22× and the terrain rose into tall ridges.
8. **Palette button.** Cycles Aurora → Nebula → Ember → Glacier → Spectrum → Aurora, and recolours terrain and Julia inset instantly.
9. **Height button.** Cycles 1× → 1.8× → 0.4× → 1×, and the terrain relief changes visibly.
10. **Dragged the background.** It orbits the camera. Sensitivity is high: a 300 px drag took the view nearly to the horizon.
11. **Home.** Resets the fractal to −0.65 + 0i at 1×, but **does not reset the camera orbit**.
12. **Dive button.** Auto-zooms into "Seahorse Valley". The label appears in the HUD and the button turns into a highlighted "Stop dive". It reached 331× after 8 s, 44,135× after 18 s, and ≈9.4×10⁵ when stopped. (`04-dive-44k-side.jpg`)
13. **Orbited to a top-down view at ≈1e6× zoom.** Boundary detail still resolves and there's no precision breakdown. There are dense spiky "grass" artefacts along the boundary and faceted, flat-shaded polygon patches inside the set. (`05-deepzoom-1e6-top.jpg`)
14. **Immerse.** Switches to a first-person, landscape-scale view: you stand on the fractal terrain under the nebula sky, and the button becomes "Tabletop". It's striking, but it shows terraced, blocky slabs and smeared flat planes. (`06-immerse.jpg`)
15. **Sound toggle.** Label switches "Sound off" ↔ "Sound on". I couldn't hear the audio.
16. **Zoom out.** Zoom ÷3 (9.38e5 → 3.13e5). **Back** steps back to the previous view.
17. **Keyboard.** Escape exits to the landing page. Arrow keys, `+`, `=`, `h` and `p` did nothing.
18. **Hovered over the landscape.** The Julia inset tracks the pointer position.
19. **Exit.** Returns to the landing card, and the 3D scene keeps rendering behind it.
20. **Phone size (window 390×844 → 446×741 viewport, the browser's minimum).** The landing card reflows well. In explore, the HUD and Julia inset scale down and there's no page-level horizontal scroll, but the toolbar (`nav`, `overflow-x:auto`, `flex-wrap:nowrap`) is 865 px wide in 446 px. "Palette" is cut off and Height, Immerse, Sound and Exit sit offscreen, reachable only by horizontal scroll with no visual hint. Buttons are 42 px tall, which is OK for touch. (`03-phone-390.jpg`)
21. **Restored the window size** (viewport back to 1203×950) and closed my tab.

No WebXR emulator was installed, so I didn't enter VR/AR sessions.

## Overall score: 8 / 10

## Top 5 issues

1. **Major: phone toolbar overflows and hides controls.** At 446 px the bottom `nav` is 865 px wide (`overflow-x:auto`, `nowrap`). Exit, Immerse, Height and Sound are offscreen with no scroll cue. *Fix:* wrap to two rows, collapse the secondary actions into a "⋯" menu, or use icon buttons below about 600 px.
2. **Major: rendering artefacts at high zoom and in Immerse.** Dense spiky "grass" aliasing along the boundary, faceted flat-shaded polygons inside the set, and terraced slabs and smeared planes in Immerse (screenshots 05 and 06). *Fix:* filter or limit height by local derivative and distance, smooth interior shading (e.g. distance estimate), and raise raymarch step precision near the camera in Immerse.
3. **Minor: possible frame-rate collapse.** In the first session rAF ran at ~600 ms per frame (2 fps) on a desktop RX 6650 XT with the main thread idle. Later sessions held 60 fps, and I couldn't reproduce it. *Fix:* add an adaptive-resolution or fps governor so a transient stall degrades resolution instead of the frame rate. That matters in an HMD.
4. **Minor: camera controls.** Home resets the fractal but not the orbit. The orbit drag is very sensitive, and there's no keyboard navigation (arrows, +/−, WASD). *Fix:* make Home reset the camera pose too, lower the orbit gain, and add keyboard pan/zoom/orbit.
5. **Minor: XR-unavailable message is slightly inaccurate.** It says "This browser has no WebXR" when `navigator.xr` exists but there's no XR device or runtime. The hidden buttons also give no hint of what users would see on a headset. *Fix:* say "No VR/AR device detected", and optionally show disabled VR/AR buttons with a tooltip explaining how to open the page on a Quest, Pico or phone.

## Strengths

- Polished first impression: the live 3D room appears right away behind an elegant landing card, with zero console noise and an FCP of about 70 ms.
- A genuine 3D *room*: a sky dome with nebula and stars, grid floor, pillars, light rings, and the Mandelbrot height field presented as a holographic tabletop. Immerse lets you stand inside the landscape.
- Deep-zoom capability: the auto "Dive" reaches about 1e6× in Seahorse Valley with the detail intact, and the HUD names the location.
- Rich, working controls: click-to-dive, wheel zoom, orbit, Back/Zoom out/Home, 5 palettes, 3 height levels, sound, and a live Julia-set inset that follows the pointer.
- Thoughtful XR and mobile paths: `isSessionSupported` gating, a browser fallback, and "Look around" and "Cardboard" modes for phones without WebXR.

## Verdict

This is a high-quality, visually striking WebXR Mandelbrot experience: a real virtual room, a 3D height-field fractal, deep zoom, and a full set of working controls, with clean load and console behaviour. The main weaknesses are the phone toolbar overflow, the aliasing and terracing at high zoom and in Immerse, and an unreproduced early frame-rate stall. The XR entry is gated properly but couldn't be exercised on this desktop.
