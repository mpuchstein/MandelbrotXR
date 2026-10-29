# HTML + Transcript Judge — blind ranking

## Ranking criteria

1. **XR path correctness (30%)**: whether the immersive VR/AR render loop and session setup in the code would actually work on a Quest/Pico/Android, since that is the "done when" condition.
2. **3D Mandelbrot quality and depth (20%)**: whether there is a real 3D representation of the set, and how far you can explore it (zoom depth, precision, detail).
3. **Cross-device usability (20%)**: XR input (controllers, hands, transient pointer), phone fallbacks (touch, gyro, stereo), iOS handling, and graceful degradation; the prompt names HMDs *and* phones.
4. **Prompt-specific fit (15%)**: v0 needs three.js and a reasonable answer to the obsolete three.xr.js request; v1 needs visual "wow" and good usability.
5. **Transcript honesty and verification (15%)**: whether the claims in the transcript and UI match the code, and whether the testing done (emulator, shader validation, numeric checks) supports them.

## Ranking

| Rank | Candidate | Prompt | Justification |
|---|---|---|---|
| 1 | B | v1 | Raw WebGL2 with perturbation deep zoom to about 4e-11, a guided dive tour, a Julia inset, AR hit-test placement, haptics, sound, and Cardboard/gyro for iPhone. The XR loop is correct, with a reference-space fallback. Tested in the IWER emulator. Its claims match the code. It needed three turns. |
| 2 | A | v0 | Bundles three.js r186 and justifies replacing the archived three.xr.js. Deep zoom via perturbation (about 1e-12), a plinth terrain, a context wall screen, a tour, an AR room toggle, gyro and stereo modes, and a CPU cross-check hook. Tested thoroughly, but it took four turns. |
| 3 | D | v0 | Bundled three.js r186 with in-file docs on the three.xr.js substitution. Worker-computed relief inside a gallery, two AR modes (full room or tabletop), teleport rings, snap turns, a minimap and split stereo. Emulator-tested, one turn. The fractal is shallow (CPU mesh at most 288×216), and the app code is minified. |
| 4 | E | v1 | Sibling build to D: an observatory room, a contoured relief, four destinations, sound, gaze-dwell, teleport and snap turn, all IWER-tested and offline. The wow factor is limited by the CPU-mesh fractal, and AR keeps the whole opaque room instead of adapting to passthrough. |
| 5 | G | v1 | Vertex-shader Mandelbrot terrain plus extra Mandelbulb and "canyon" modes, laser controllers, locomotion, an AR mode that hides the room, and gyro. Depends on CDNs (three r128, Tailwind) and shipped first with a shader compile error. Raycasts hit the undisplaced plane. Nothing was tested. |
| 6 | C | v1 | Clean dependency-free WebGL2 room with a GPU relief, locomotion, grab and hand pinch, and adaptive quality. But its fractal zoom stops re-rendering beyond about 16× (texDirty bug), the Android gyro lacks the −90° correction, and the in-XR exit button is hidden. |
| 7 | F | v1 | Minimal WebGL2 heightfield with a starfield. VR rendering is correct, but there is no XR input at all, AR clears opaque so passthrough is hidden, and the "room" is just a floor plane. The UI claims pinch-zoom and "orbit trails", and neither exists. |
| 8 | H | v1 | Raymarched slab looks nice on screen, but the XR loop reads the nonexistent `xrView.viewport`, so VR/AR crashes on its first frame. It also ignores the projection matrix and looks along +Z. The hints advertise tap-to-place, ESC and a reticle, and none of them is implemented. |

## Special elements

- **A, B — perturbation deep zoom:** both compute a float64 reference orbit on the CPU, upload it as an RG32F texture and iterate fp32 deltas with Zhuoran rebasing on the GPU, which goes orders of magnitude deeper than every other candidate's naive float32 escape-time.
- **A — prototype monkey-patch:** when the session didn't grant `layers`, it does `delete XRWebGLBinding.prototype.createProjectionLayer` to stop three.js r186 using projection layers, a bold low-level compatibility hack that no other candidate tried.
- **A, D — three.xr.js substitution:** both recognised that the requested three.xr.js is archived WebVR-era code and replaced it with three.js's native WebXRManager, explaining why (D even documents it in the in-page guide), which is the right reading of an outdated v0 requirement.
- **B — Julia inset at the pointer:** a live Julia-set panel driven by whatever point the controller, gaze or mouse is aiming at adds real mathematical insight on top of the visual effect.
- **B — AR hit-test placement:** it is the only candidate that requests `hit-test` and shows a surface reticle for placing the hologram on handheld Android AR.
- **D — two AR modes:** it offers a choice between a full-size room around the user and a placeable tabletop miniature, a thoughtful answer to "AR glasses" plus "virtual room".
- **E — gaze-dwell and ambient sound:** a dwell-to-select fallback for input-less headsets, plus WebAudio ambience, are usability and atmosphere touches that most of the others lack.
- **E — AR not adapted:** although three.js clears transparently under alpha-blend, E never hides its opaque observatory geometry in AR, so "Enter AR" mostly shows the virtual room rather than passthrough.
- **G — Mandelbulb mode and CDN dependency:** it adds a raymarched Mandelbulb (a different fractal) and is the only candidate that needs the network at runtime (three r128 and the Tailwind CDN).
- **G — broken first delivery:** the transcript shows the first build failed with a fragment-shader compile error (`modelMatrix`/`inverse()` in the fragment stage), fixed only on an automatic "fix error" turn.
- **C — zoom claim vs code:** the transcript promises "right stick zoom into the set, iterations auto-scale up to ~760", but `setHalf` only marks the texture dirty when the rounded iteration count changes, so zooming freezes once it hits the 320/760 clamps.
- **C — delivery struggle:** much of the transcript is spent fighting a read-only GitHub integration before the file was finally pasted inline, which is honest but costly.
- **F — UI and transcript overclaim:** the panel text advertises "orbit trails", and the hint promises "pinch to zoom", yet the code has neither, only a wheel handler and no trails.
- **H — fatal XR bug behind a claim of success:** the transcript says immersive VR/AR were verified, but `xrView.viewport` is undefined (it should be `layer.getViewport(view)`), so the XR frame loop throws before it re-queues itself.
- **A, B — multi-turn completion:** both hit tool limits and needed two or three user "Continue" prompts before delivering, which counts against them as a usability cost but not against the deliverable.

## Summary of tests and approach

Static review only: no browser and no server. I read each TRANSCRIPT.md in full or by section, then reviewed the application code in each index.html, skimming the bundled three.js (A, D, E; G uses a CDN). For the readable sources (B, C, F, G, H, and A's app script) I traced the XR session setup, the per-view render loop (viewport, projection and view matrices, clear alpha in AR), input handling, the phone fallbacks and the fractal pipeline. For minified D and E I grepped the bundled app code for the claimed features (requestSession options, reference-space fallback, snap turn, worker, dwell, AR background) and checked that three.js's alpha-blend background clearing was present. I cross-checked every major transcript claim against the code, which exposed H's crashing XR loop, C's zoom/re-render bug, and F's and H's advertised-but-missing features. Each candidate was scored against its own prompt version using the weighted criteria above.
