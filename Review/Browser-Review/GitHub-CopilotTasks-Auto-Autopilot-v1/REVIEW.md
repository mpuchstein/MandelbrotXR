# Browser Review — candidate-04

| Criterion | Score | Reason |
|---|---|---|
| 1. Loads & renders | 7 | Clean load with zero console messages and a WebGL2 canvas; the start card shows in under a second, and the 3D scene appears only after "Explore on screen". |
| 2. Done-when (desktop-checkable) | 4 | A 3D Mandelbrot heightfield sits on a floor under a starfield, but there is no "room", and on this desktop the XR path is a silent dead end. |
| 3. Visual wow effect | 3 | A low-res magenta extruded plateau with jagged, stretched wall faces. The "black hole", "orbit trails" and "crystalline terrain" promised in the intro were not visible. |
| 4. Usability & controls | 5 | Drag-orbit, wheel zoom and double-click reset all work, with a hint line. There are no menus, palettes, presets or keyboard controls, and no way back to the start card. |
| 5. Robustness | 6 | 60 fps, no errors, the canvas tracks resizes, and there is no horizontal scroll at 446 px. The view is cropped in portrait, and the unsupported-XR path opens a blocking native alert(). |
| 6. XR readiness & messaging | 4 | "Enter VR" and "Place in AR" stay enabled although `isSessionSupported` returns false for both. Clicking one does tell the user it is unsupported ("VR is not supported on this device." / "AR is not supported on this device."), but in a blocking native `alert()` rather than in-page UI, and with no hint of what to do instead. |

## Steps performed
1. **Loaded http://localhost:8704/ and waited 3 s.** The start card appeared: title "MANDELBROT / INFINITE ROOM", a short blurb, and buttons ENTER VR, PLACE IN AR and EXPLORE ON SCREEN. The background behind the card is plain black, so the scene does not preview. Console: no messages, even after a reload with tracking on. *(screenshots/01-start-overlay.jpg)*
2. **Introspected the page with JS.** `navigator.xr` exists. `isSessionSupported('immersive-vr')` and `isSessionSupported('immersive-ar')` both return `false`. There is a single inline script and no external libraries. The canvas uses a WebGL2 context, not lost.
3. **Clicked ENTER VR** (a real click, then again via JS with error, rejection and console hooks installed). Nothing changed in the page DOM and nothing was logged, so my first draft wrongly called this a silent no-op. **Observed by the operator, not by me:** the click opened a native dialog, "localhost:8704 says: VR is not supported on this device.", with an OK button. My page screenshots don't capture native dialogs. The dialog blocked the automation extension until the operator dismissed it by hand.
4. **Clicked PLACE IN AR.** As with VR, nothing showed in the page; per the re-test in 4b, it opens the equivalent native alert.
4b. **Confirmed it myself:** re-tested in a fresh tab with `window.alert` stubbed to `console.log`. The JS clicks logged `ALERT: VR is not supported on this device.` and `ALERT: AR is not supported on this device.`, which confirms the unsupported path uses blocking `alert()` dialogs.
5. **Clicked EXPLORE ON SCREEN.** The card disappeared, and the hint "Drag to look · pinch to zoom · double tap to reset" appeared at the bottom. The scene shows a magenta, extruded Mandelbrot heightfield (cardioid and bulb readable from above) on a dark-blue floor slab, with a coloured starfield. *(screenshots/02-explore-default-view.jpg)* (My first physical click on this button didn't register because the window size changed between the screenshot and the click; the JS click worked.)
6. **Dragged horizontally and vertically.** The camera orbits and tilts smoothly. From above, the set's silhouette is recognisable, but the walls are coarse vertical spikes and look stretched. Colour is limited to a magenta-to-blue gradient.
7. **Mouse wheel.** Zoom in and out works smoothly, and you can fly right up to the plateau. Close up, the low mesh resolution is obvious: jagged steps and smeared faces.
8. **Keyboard** (W ×20, Right arrow ×10, Escape). No effect. Escape does not return to the start card, and no other way back exists short of reloading.
9. **Double-click.** Resets the camera to the default view. Works.
10. **Frame rate.** A 3 s requestAnimationFrame count gave 60.2 fps. No errors were collected during the whole session.
11. **Resized to 390×844 (viewport 446×741).** In the scene, the canvas resized correctly and there is no horizontal scroll. The fractal is cropped at both sides, though, because the camera or FOV is not adjusted for portrait, and the hint wraps to two lines. *(screenshots/03-phone-scene.jpg)*
12. **Reloaded at phone size.** The start card fits with a 16 px gutter, the title wraps to two lines, and buttons are 47 px tall, which is touch-friendly. *(screenshots/04-phone-overlay.jpg)*
13. **Restored the window** to 1683×1056 and closed my tab.

## Overall score: 4 / 10

## Top 5 issues
1. **Major: the unsupported-XR path is a blocking `alert()` behind always-enabled buttons.** Evidence: steps 3–4b. `isSessionSupported` returns false for both modes, yet the buttons stay enabled. Clicking one does tell the user that VR or AR is unsupported, but through a native modal ("localhost:8704 says: VR is not supported on this device.", seen by the operator and confirmed via the alert stub). The modal freezes the page, wedges browser automation, and doesn't say what to do instead (use a headset browser, HTTPS, or Explore on screen). A disabled or relabelled button would avoid the dead-end click altogether. **Fix:** check support at load, then disable or relabel each button ("VR needs a headset browser / HTTPS"). Show errors inline on the card instead of using `alert()`, and wrap `requestSession` in try/catch.
2. **Major: weak visuals, and the intro promises things the scene doesn't show.** Evidence: steps 5–7, screenshot 02. The scene is a coarse magenta heightfield with stretched spike walls. The black hole, orbit trails and crystalline terrain the intro text describes were not visible. **Fix:** use a much denser mesh, or ray-marched or shader-based height with smooth normals; use iteration-based palettes, emissive or glow edges and fog. Then either build the orbit trails or remove the claim.
3. **Major: no "virtual room".** Evidence: steps 5–7. There is only a floor slab in a starfield, with no walls, room or environment framing the exhibit. **Fix:** add a room shell, such as a gallery, walls with the 2D set projected on them, or a pedestal, so it reads as a room and gives scale cues in VR.
4. **Major: the exploration feature set is minimal.** Evidence: steps 6–9. There are no palettes, presets, iteration or zoom-depth control, no way to zoom into the fractal itself (only the camera moves), and no keyboard controls or way to exit back to the menu. **Fix:** add a small HUD (palette, iterations, presets such as Seahorse Valley), deep-zoom into the complex plane, WASD/arrow keys, and Esc to return to the menu.
5. **Minor: portrait framing crops the subject.** Evidence: step 11, screenshot 03. On a phone-shaped viewport the fractal overflows both sides. **Fix:** in portrait, increase the camera distance or use a horizontal-FOV-preserving projection.

## Strengths
- Clean, stylish start card with clear three-way entry (VR / AR / on-screen) that also fits a phone screen.
- Zero console errors or warnings across the whole session, using raw WebGL2 with no external dependencies.
- Smooth 60 fps, with responsive orbit, zoom and reset.
- A concise on-screen control hint that covers both touch and mouse.
- The canvas tracks window resizes correctly, with no layout overflow.

## Verdict
The page is technically clean and runs smoothly, and the start card is attractive. What you get after it is a coarse magenta heightfield on a floor, far from the "highest possible wow" brief, and nothing like a room. On a device without XR, the VR and AR buttons stay enabled and only pop a blocking `alert()`, so the immersive path can't be judged here and the fallback UX is crude.
