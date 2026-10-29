# Browser Review — candidate-01

| Criterion | Score | Reason |
|---|---|---|
| 1. Loads & renders | 9 | A finished 3D frame appears in under 1 s, with zero console messages (errors or warnings) across the whole session. It is one self-contained inline script on WebGL 2 with no CDN dependencies. |
| 2. Done-when (desktop-checkable) | 8 | It is a real room: a circular observatory with pillars, rings, wall typography, a plinth and a 3D escape-time heightfield of the set. The XR path exists (a hidden "Enter AR" button and a device-capability dialog), but entering XR can't be confirmed without a device. |
| 3. Visual wow effect | 8 | The overview is striking: neon contour lines, glowing rings, layered terraces and three good palettes. It is weaker at zoomed destinations, where a square slab overhangs the round plinth and the set interior is a dark flat plateau. |
| 4. Usability & controls | 8 | Destinations, palette, orbit, zoom, home, sliders, walk mode, keyboard shortcuts and an excellent help sheet all work. The zoom buttons can drop you into a featureless flat area, and the HUD copy overlaps text in the 3D scene. |
| 5. Robustness | 7 | No errors, the canvas tracks resizes, and Home/R recovers from any state. Fullscreen didn't engage here and gave no feedback, a first H press was swallowed by button focus, and frame rate couldn't be measured (the harness throttled requestAnimationFrame). |
| 6. XR readiness & messaging | 9 | The "XR info" dialog lists 3D room / VR / AR / Connection status and explains HTTPS, Quest/PICO/Steam Frame/iPhone support and in-headset controls (teleport, snap turn, gaze-dwell). The Enter buttons are hidden when unsupported, and the copy is clear and honest. |

## Steps performed

1. **Created own tab, loaded http://localhost:8765/, waited 3 s, took a screenshot.** Outcome: a complete scene almost immediately (`01-initial-load.jpg`). It shows the title "The infinite room.", a glowing plinth with a teal/violet/orange contour-lined Mandelbrot heightfield, and a cylindrical room with pillars, a halo ring and "MANDELBROT / z² + c" wall typography. The bottom dock has destination, palette, orbit, zoom, home and Controls; the top bar has sound, fullscreen, help and "XR info".
2. **Reloaded with console capture active and read the console.** Outcome: **no console messages at all**, either at load or later. Introspection showed `navigator.xr` present, `immersive-vr` false, `immersive-ar` false, 1 canvas, WebGL 2.0 and only inline scripts.
3. **Clicked "XR info".** Outcome: a "Step inside." modal (`02-xr-info-dialog.jpg`): *Interactive 3D room: Available; Immersive VR: Unavailable here; Immersive AR: Unavailable here; Connection: Secure*. It adds HTTPS/browser guidance and notes on Quest/PICO/Steam Frame/iPhone, plus an "Explore on this screen" button. Clear and accurate. (Minor: "Unavailable here" is coloured in the same teal as "Available".)
4. **Palette button (×2).** Outcome: switches Aurora → Nebula (violet/rose) → Solar (amber/ember) instantly. The whole room's accent lighting re-tints, not just the fractal. Very effective.
5. **Next destination (×3): Seahorse valley, Elephant valley, The little universe.** Outcome: smooth animated transitions, and the exhibit card updates (name, tagline, zoom factor 77.78× / 43.5× / 100×). The zoomed views are less attractive (`03-seahorse-valley.jpg`). The heightfield is a square slab that overhangs the round plinth, and half of it is a dark flat plateau (the set interior), so the "wow" drops compared with the overview.
6. **Opened "Controls" ("Make it yours." panel).** Outcome (`04-controls-panel.jpg`): light-spectrum select, landscape-height and exhibit-scale sliders, surface detail (Automatic / Light / Balanced / Fine), Pause light, Hide interface, Walk in room, Motion look, Ambient sound and a Gentle-motion checkbox. Dragging the sliders changed height (1.75×) and scale (0.70×) live.
7. **Walk in room.** Outcome: the camera drops to eye level facing the exhibit, the panel and hero copy hide, and the hint changes to "Drag to look · WASD / arrows to walk · R to return home". Drag-to-look rotates freely around the room. A held W key moved forward only slowly. The hint text sits on top of the in-world "THE MANDELBROT SET" label, which makes both hard to read.
8. **R key.** Outcome: returns home and resets destination and sliders, but stays in walk mode.
9. **Toggled back to "Orbit exhibit", then dragged on the canvas and used the mouse wheel.** Outcome: orbit drag works, and the wheel "approaches" with smooth damping.
10. **Double-clicked the landscape ("dive").** Outcome: zooms into the clicked point, and the destination becomes "Your discovery" (2.40×).
11. **Zoom-in button ×2, then zoom-out ×1.** Outcome: it zooms around the view centre. After the dive it landed in a nearly flat, featureless red plane with one or two contour lines, so it is easy to get "lost".
12. **Home button and "Toggle slow orbit".** Outcome: Home restores the overview, and the orbit toggle starts a slow auto-rotation (`aria-pressed` updates correctly).
13. **Help ("How to explore") button.** Outcome: an excellent guide covering touch / mouse / keyboard / headset controls, an explanation of escape-time height vs. a Mandelbulb, and offline/HTTPS notes. Esc closes it.
14. **H key (hide interface).** Outcome: the first press did nothing because focus had returned to the help button. With focus on body it hides all HUD and leaves a small "Show controls" button; pressing H again restores the HUD.
15. **Ambient sound button.** Outcome: the toggle works (label flips to "Disable ambient sound", `aria-pressed=true`); audio output was not verified. Then switched it off again.
16. **Fullscreen button (×2).** Outcome: `document.fullscreenElement` stayed null and there was no visible feedback. This may be harness-related, but nothing told the user that it failed.
17. **Frame-rate probe** (requestAnimationFrame counter, light JS). Outcome: about 1.3–1.7 fps regardless of the quality setting (Automatic vs Light) and even with the canvas hidden; the main thread was idle (setTimeout ran at full rate). That points to the browser/window throttling rAF in this automation setup, not to the page, so **the frame rate couldn't be measured**. Visually, every transition I captured looked smooth and complete. Side note: with the throttled rate, "Automatic" quality had dropped the render scale to about 0.85×.
18. **Phone layout.** Resized the window (the tiling WM settled at a 446×741 viewport; a 386×840 same-URL iframe was also checked briefly and then removed). Outcome (`05-phone-layout.jpg`): there is no horizontal scroll, the dock collapses (zoom, sound and fullscreen hidden; Controls becomes an icon), and the top bar keeps help and XR info. The Controls panel becomes a scrollable sheet. Issues: the hero heading "The infinite room." overlaps the in-world "MANDELBROT" ring text, and the hero plus exhibit card take about 50 % of the vertical space. Dock buttons are 33×41 px, slightly under the 44 px touch guideline. Walk mode at phone width hides the hero copy and works; the movement pad was not shown, which is expected without a touch pointer.
19. **Restored window size** (the WM gave 1203×906) and re-read the console. Outcome: the canvas resized to match exactly and the console was still empty. DOM check: there is a hidden "Enter AR" button; the XR entry buttons are hidden when unsupported, as the dialog says.
20. **Closed my tab.**

## Overall score: **8 / 10**

## Top 5 issues

1. **Zoomed destinations lose the wow.** Severity: major. Evidence: `03-seahorse-valley.jpg`; Elephant valley and Little universe look the same. The square heightfield slab overhangs the circular plinth, and the set interior shows as a large dark flat plateau that dominates the view. Fix: clip the heightfield to a disc that matches the plinth, or fade its edges with a radial alpha. Give the interior a subtle shaded or emissive treatment (e.g. orbit-trap or distance-estimate shading), or lower it instead of raising it.
2. **Zoom buttons can strand the user in a flat void.** Severity: major. Evidence: step 11; after a dive, two zoom-ins gave a featureless red plane. Fix: zoom toward the nearest boundary or highest-detail point, or snap the zoom centre to the boundary. Show a "lost? ⌂ Home" hint when the visible height variance is near zero.
3. **HUD text collides with in-world text.** Severity: minor. Evidence: the phone screenshot shows "room." over the "MANDELBROT" ring; on desktop, the walk-mode hint overlaps the "THE MANDELBROT SET" plinth label and the hero copy overlaps the "01 / THE INFINITE ROOM" wall label. Fix: give hints and hero copy a subtle backdrop or scrim, or offset the camera framing on narrow viewports. Collapse or fade the hero copy after first interaction on phones.
4. **Fullscreen gives no feedback when the request fails.** Severity: minor. Evidence: step 16, `fullscreenElement` stayed null. Fix: catch the `requestFullscreen()` rejection and show a short toast. Hide the button where fullscreen isn't permitted (e.g. iPhone Safari).
5. **Small touch targets and focus-sensitive shortcuts.** Severity: minor. Evidence: dock buttons are 33×41 px at phone width; the first H press was ignored while a button had focus. Fix: use a minimum hit area of 44×44 px. Handle H/R globally unless focus is in a text input or select; buttons are fine.

## Strengths

1. Polished, coherent "observatory" art direction. The palettes re-tint the whole room, and the neon contour terraces of the overview are genuinely striking.
2. Excellent XR messaging. A capability dialog with per-mode status, HTTPS guidance and device-specific notes, plus in-headset interaction docs (teleport, snap turn, grip-to-summon panel, gaze-dwell fallback).
3. A rich, well-labelled control set: destinations, double-click dive, walk mode with WASD, motion look, sliders, quality presets, hide-UI, reduced-motion option and a thorough help sheet. ARIA labels and `aria-pressed` states are present.
4. Clean runtime. Zero console output, a single self-contained file, instant first frame, and the canvas resizes correctly.
5. A thoughtful responsive layout. The dock collapses sensibly at phone width, there is no horizontal scroll, and the Controls panel becomes a scrollable sheet.

## Verdict

This is a polished, production-feeling WebXR exhibit: it loads instantly with no errors, presents a convincing virtual observatory around a 3D escape-time Mandelbrot, and explains XR availability better than most. The main weaknesses are visual and navigational once you zoom in: the slab overhangs the plinth, the flat interior plateaus are dull, and the zoom buttons can lead into empty areas. There is also minor HUD/text overlap on small screens. Actual immersive VR/AR entry couldn't be verified on this desktop.
