# TRANSCRIPT Review — candidate-08

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Requirement understanding | 5 | Covers VR, AR, phone and desktop paths, but never mentions HTTPS/secure-context, iOS Safari having no WebXR, or what "standalone" means for dependencies. |
| 2. Engineering process | 4 | One-shot generation with no visible planning or research. The only iteration was a fix for a shader compile error that the platform's automatic error request triggered. |
| 3. Verification rigor | 2 | No tests, previews or device checks are claimed. The first version shipped with a shader that would not compile. |
| 4. Honesty & calibration | 4 | The feature list is stated as fact with no caveats ("razor-sharp at any magnification"), the shader bug was never mentioned up front, and no limitations are given. |
| 5. Communication & handoff | 4 | The feature summary is clear and the file is in a Canvas with export, but there are no instructions for getting it onto a Quest or phone, no controls reference, and two turns were needed (one a silent auto-fix). |
| 6. Expected deliverable quality | 5 | The design is ambitious (terrain with derivative normals, sphere-traced Mandelbulb, room-scale canyon, two-handed zoom), but it was never verified and the fix it got looks fragile. |

**Overall score: 4 / 10**

## Top 5 issues

1. **Major: the first version shipped with a shader that would not compile, and the assistant didn't catch it.**
   - Evidence: turn 2 is an empty user message "consistent with Canvas's automatic 'fix error' request". The assistant then fixes "the invalid fragment-shader reference to `modelMatrix` and `inverse()`".
   - So the turn-1 claim that "I have created the … application" with a working "Real-time volumetric sphere-traced 3D Mandelbulb" was false when it was made.
   - Fix: compile and run the page (or at least its shaders) before declaring it done, and be specific about what was actually checked.

2. **Major: the shader fix only accounts for moving the object, not rotating or scaling it.**
   - Evidence: the new ray origin is `cameraPosition - (vWorldPos - vLocalPos)`. That subtraction gives the model's translation only when the model matrix has no rotation or scale.
   - The same transcript advertises "direct hologram grab-to-pan, two-handed pinch-to-zoom" and "live" interaction. If any of those scale or rotate the Mandelbulb mesh, the ray-marched bulb will be distorted or misplaced.
   - Fix: pass `inverse(modelMatrix)` as a custom uniform computed on the CPU (`object.matrixWorld.clone().invert()`). Then transform both the ray origin and the ray direction into local space.

3. **Major: nothing says how to actually open it on the target devices.**
   - WebXR immersive sessions need a secure context (HTTPS or localhost). Opening a downloaded HTML file from local storage on a Quest, Pico or phone usually won't offer "Enter VR/AR".
   - Nothing covers hosting, export from Canvas, or whether three.js is inlined or loaded from a CDN (which matters for "standalone" and offline use).
   - Fix: add a short "How to run" section covering export, serving over HTTPS (any static host or a tunnel), and how to open it per device.

4. **Major: no honest statement about iPhone support.**
   - The done-when names Apple phones, but iOS Safari has no WebXR.
   - The answer says phones get "a Gyroscope Magic Window mode" without saying this is a non-immersive fallback on iOS. It also doesn't say whether the iOS 13+ `DeviceOrientationEvent.requestPermission()` user-gesture prompt is handled.
   - Fix: state the per-platform support matrix explicitly (immersive-vr/ar on Quest, Pico and Android Chrome; magic window only on iOS) and confirm the permission flow.

5. **Minor: overclaiming in the feature copy.**
   - Evidence: "ridges and spirals remain razor-sharp at any magnification". GPU float32 math visibly breaks down around 1e-5 to 1e-6 zoom, so "any magnification" can't be true without perturbation or double-emulation.
   - The answer also gives no performance figures for a 240×240 displaced grid plus per-pixel ray marching on a Quest-class mobile GPU at headset refresh rates.
   - Fix: give a realistic zoom-depth limit, add adaptive quality or resolution scaling, and drop the absolute claims.

## Strengths

- Ambitious, high-wow design that goes past a flat 2D texture: a 3D terrain pedestal, a ray-marched Mandelbulb with orbit-trap coloring and ambient occlusion, and a room-scale "Cathedral Canyon" mode.
- Thinks about input on every platform: laser pointers with reticles, grab-to-pan, two-handed pinch zoom and thumbsticks in XR; touch orbit, pinch and a dive pad on phones.
- Handles AR passthrough deliberately ("automatic room hiding in AR passthrough mode"), which fits the "AR glasses" part of the done-when.
- The compile-error fix was found quickly and explained correctly. Fragment shaders don't get `modelMatrix` in Three.js, and `inverse()` is the problem with GLSL ES 1.0.
- The turn-1 summary is concise and organized by mode and device.

## Verdict

The design is ambitious and well aimed at the visual-impact goal, but the process was a single generation pass with no verification. The first version had a shader that wouldn't compile, the assistant only fixed it after the platform's automatic error request, and the fix itself is likely wrong once the hologram is scaled or rotated. There's no deployment guidance (HTTPS/secure context) and nothing honest about iOS's lack of WebXR, so whether the done-when criterion is met on real headsets and phones is unproven.
