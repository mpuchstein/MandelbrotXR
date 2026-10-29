# HTML Judge — blind ranking

## Ranking criteria

1. **XR correctness (30%)**: correct stereo per-view rendering, reference-space fallbacks, a render loop that survives tracking loss. If the headset view is wrong, nothing else matters.
2. **Device reach (20%)**: Quest/Pico/SteamVR controllers *and* hands, Android AR, and a real fallback for iOS Safari, which has no WebXR. The prompt names HMDs and both phone families.
3. **Mandelbrot fidelity in 3D (20%)**: how faithfully and deeply the set is rendered as a 3D object in a room (precision, resolution, zoom depth). This is the core deliverable.
4. **Usability in and out of XR (15%)**: in-headset controls, onboarding, locomotion, error and support messaging. Needed for "a person … can open … and enter".
5. **Prompt-specific goal (10%)**: v1 is judged on its "wow" effect; v0 on using three.js and how it handles three.xr.js. Each candidate is held only to its own prompt.
6. **Robustness and standalone delivery (5%)**: offline single file, performance adaptation, context-loss handling, and parse/compile checks.

## Ranking

| Rank | Candidate | Prompt | Justification |
|---|---|---|---|
| 1 | H | v1 | Dependency-free WebGL2. Perturbation deep zoom to about 1e-13 with progressive GPU jobs, AR hit-test placement, hands, transient pointers, haptics, Cardboard stereo for iOS, Julia inset, guided tour, procedural sky. All 22 shaders validate. The most complete and correct entry. |
| 2 | E | v0 | Bundled tree-shaken three.js r186. Perturbation deep zoom to 1e-12, in-VR canvas panel, hands, snap turn, locomotion, gyro and Cardboard modes, context wall screen. Careful XR edge-case handling. Swaps three.xr.js for WebXRManager, justified only in a code comment. |
| 3 | D | v1 | Polished, accessible offline gallery: bundled three.js, worker-built mesh, spatial VR panel, gaze-dwell buttons, teleport, snap turn, hand pinch, haptics, adaptive foveation and quality. CPU mesh limits zoom depth; the minified app code is hard to audit. |
| 4 | G | v0 | Bundled three.js r186 with a worker-built relief, minimap, full-size or tabletop AR with placement, floor teleport, split-screen stereo. Explains in-app why three.xr.js is obsolete. Coarse 192×144 relief and minified app code keep it below D. |
| 5 | B | v1 | Most features: spatial VR UI, grab-pan, two-hand zoom, Mandelbulb and Julia modes, audio synth, gyro. But it loads three r128 and the Tailwind play CDN at runtime, runs float32 deep zoom, and a 1024-iteration fragment loop is a performance risk on Quest. |
| 6 | F | v1 | Clean raw WebGL2: GPU-rendered Mandelbrot texture displaces the mesh in a full room; hand pinch-grab, flying, adaptive quality. Bug: re-rendering the texture inside the XR loop rebinds framebuffer null, so one eye renders off-target whenever you zoom. |
| 7 | C | v1 | Minimal WebGL2 heightfield with stars. The XR loop stops for good if `getViewerPose` returns null once. The viewer spawns inside the 1.85 m plateau. No XR interaction, uses `alert()`, and the advertised pinch-zoom isn't implemented. |
| 8 | A | v1 | Raymarched SDF. In XR, the forward vector is the view's +Z (it looks backwards), projection matrices are ignored, and per-eye UVs use the full framebuffer size. 96 steps × 80 iterations per pixel can't run on headsets. Only on-screen orbit works. |

## Special elements

- **H, E — perturbation-theory deep zoom** (float64 CPU reference orbit in an RG32F texture, float32 GPU deltas, row-scissored progressive jobs, cross-faded buffers): the only candidates that zoom past float32 limits, to roughly 1e-12 to 1e-13.
- **H — van Wijk & Nuij smooth zoom-pan flights plus async PBO readback with `fenceSync`** for ray-casting the hologram: no other candidate does stall-free GPU→CPU readback or optimal zoom-pan paths.
- **H — handheld-AR detection via `interactionMode === 'screen-space'` with hit-test reticle placement**: the only phone-AR flow that places the model on a detected real surface.
- **H, E, G — Cardboard/split-screen phone stereo**: the only route to a stereo "headset" view on iPhones, where WebXR doesn't exist.
- **E — deletes `XRWebGLBinding.prototype.createProjectionLayer` when the session didn't grant `layers`**: an unusual, targeted workaround for a three.js r186 projection-layer pitfall that no one else addresses.
- **E — context "wall screen" at 3× the terrain span**: the only candidate that shows where you are in the set while you're zoomed in.
- **D — gaze-dwell activation ("look at a button for 3 seconds")**: the only accessibility path for headsets with no controllers or hand tracking.
- **D, G — inline Blob Web Worker building the fractal mesh, inside a minified bundled build**: the only candidates that move fractal computation off the main thread.
- **G — in-app explanation that three.xr.js is archived, with links**: the only v0 candidate that tells users in the UI why that part of the prompt was replaced.
- **B — procedural Web Audio drone tied to zoom, plus Mandelbulb raymarch and Julia-morph modes**: the widest creative scope, and the only candidate using runtime CDNs (three r128, Tailwind).
- **F — Mandelbrot rendered to a half-float texture (RGBA8 fallback) and sampled in the vertex shader for displacement, plus pinch detection from hand-joint distance**: a GPU heightfield pipeline no one else uses in this form.
- **A — full-screen raymarched extrusion of the Mandelbrot boundary**: the only pure-raymarch approach, though its XR camera maths is broken.

## Summary of tests and approach

I reviewed every file statically. I read the readable application code in full or in large parts: A, C and F completely, and the main sections of B, E and H. Where three.js was bundled (D, E, G), I skimmed the library and pulled the minified app code out by grepping for keywords: `requestSession`, `getHand`, `teleport`, `haptic`, `Worker`, `setFoveation`, `deviceorientation`. I extracted every inline `<script>` with a small Python script, and all 9 passed `node --check`. Using a Node helper, I pulled the GLSL out of the raw-WebGL candidates (A, C, F, H) and ran each shader through `glslangValidator`; all compiled. I traced XR maths by hand: A's quaternion-to-forward conversion, F's framebuffer binding order inside the XR loop, and C's per-frame `requestAnimationFrame` placement and spawn position against its heightfield formula. I also compared reference-space fallbacks, input handling (controllers, hands, transient pointers), iOS fallbacks, precision limits and external dependencies. Each candidate was scored against its own prompt version, and nothing was run in a browser.
