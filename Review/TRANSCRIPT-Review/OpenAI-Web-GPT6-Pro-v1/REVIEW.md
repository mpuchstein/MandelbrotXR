# TRANSCRIPT Review — candidate-01

| Criterion | Score | One-line reason |
|---|---|---|
| 1. Requirement understanding | 8 | Covered every listed device class and correctly called out iOS Safari's lack of immersive WebXR and Steam Frame's uncertain support, but never stated its "3D" interpretation (heightfield) or how the iPhone case meets the done-when. |
| 2. Engineering process | 8 | Three parallel workstreams, web research, a worker-based fractal engine, a fully offline build, and three real defects found and fixed during iteration. |
| 3. Verification rigor | 7 | Broad test coverage claimed (offline, layouts, touch, IWER stereo emulation), but the transcript shows only narrated summaries with no raw output; AR mode, hand/gaze input and frame rate are not shown as tested. |
| 4. Honesty & calibration | 9 | Says plainly that "Physical headset and actual iPhone testing remain unverified", hedges Steam Frame, and cites sources for platform limits. |
| 5. Communication & handoff | 8 | One turn, file attached, clear sections for open/compat/verified; hosting steps are generic and some internal jargon ("Library skill", "Xr", "Compatibility") leaks through. |
| 6. Expected deliverable quality | 8 | A self-contained 641 KB file with embedded Three.js, a real escape-time landscape, 4 destinations, an in-room XR menu, teleport/snap-turn and phone fallbacks. Likely solid, though the visual "wow" depends on how good the heightfield looks. |

**Overall score: 8 / 10**

## Rubric detail

**1. Requirement understanding (8).** The assistant grasped the done-when: it described "a dramatic virtual room" and a "real geometric Mandelbrot landscape: escape time becomes height". It went through each named device in a compatibility table. It handled the infeasible part honestly: "Safari on iOS does not currently provide immersive WebXR, so these devices use the screen-based experience". It hedged Steam Frame ("I'm not claiming support across all Frame browser builds"). It also caught the secure-context constraint: "WebXR requires a secure context; an ordinary LAN address served over plain HTTP generally does not qualify." Gaps:
- It never said explicitly that the screen-based room is how it reads the done-when for iPhones.
- It never surfaced the choice of a 2.5D heightfield over a true volumetric 3D form (e.g. a Mandelbulb or a raymarched volume).
- Apple Vision Pro, the most obvious Apple device that does support WebXR, is absent from the table.
- "AR glasses" gets only a generic row.

**2. Engineering process (8).** The work log shows parallel workstreams ("Fractal, Xr and Compatibility started working"), two rounds of web research ("Searching 5 websites", "Searched 6 websites"), and a sound architectural decision: "computes the detailed surface in a background worker… out of the headset's frame loop". It also ships a no-CDN offline bundle. Iteration was evidence-driven:
- The portrait camera "sat behind a room pillar", so it was moved.
- A double-tap was "counted twice by the browser", so it was patched.
- The VR menu "blocked the sculpture from the entrance", so it was moved and angled.

Three defects caught by its own testing is a good sign. The 17-minute session is efficient.

**3. Verification rigor (7).** What it claims to have verified:
- offline load with "zero network requests"
- layout checks in portrait and landscape
- touch drag, pinch and double-tap
- the joystick pad
- permission and fallback paths ("missing workers or denied motion/XR permissions")
- the real Three.js immersive path in the IWER emulator: stereo, controller tracking, trigger select, exit, camera restore

That is better than most. But every check appears only as "Ran command" plus a prose summary. The transcript contains no logs, screenshots, test scripts or assertions, so a reader cannot tell what was asserted versus eyeballed. Several things are not evidenced at all:
- `immersive-ar` session entry
- the gaze-dwell fallback
- real hand tracking (only "transient pinch input" in "mocked input and lifecycle checks")
- performance or frame rate on a mobile-class GPU, even though "Adaptive detail" is advertised

**4. Honesty & calibration (9).** The limits are stated up front and specifically: "Physical headset and actual iPhone testing remain unverified. The delivered file is browser- and emulator-tested". The vendor support claims carry citations. There is mild overclaiming in two places:
- The feature list presents "gaze dwell fallback" and "supported pinch input" with the same confidence as the tested features.
- "No JavaScript or shader errors appeared in those checks" is scoped correctly but cannot be checked from the transcript.

**5. Communication & handoff (8).** It needed one user turn and attached the deliverable ("[Attachment: mandelbrot-room.html]"). The answer is well structured: features, how to open, a device table, and what was verified versus not. Weaknesses:
- "Upload it unchanged to any HTTPS static host" gives no concrete route, such as a one-line local HTTPS server, a named free host, or how to get the file onto a Quest.
- Internal artifacts leak through: "using the Library skill", the "Xr/Fractal/Compatibility" stream names, and opaque "Edited 01a1880b-…:exec-…" lines.
- The final "Open file." is a dangling UI remnant.

**6. Expected deliverable quality (8).** From the transcript I expect a robust, polished app:
- self-contained, with zero network requests
- a worker-computed mesh with contour lines
- an observatory room with an in-world XR menu, grip-to-summon, teleport and 30° snap turn
- palettes, height and size controls, ambient audio, a hide-UI mode, reduced motion, and a WASD/touch walk mode

Risks:
- A heightfield can look flatter than "highest possible wow". The log itself admits glow was overwhelming the structure at one point.
- Mesh resolution limits detail at the zoomed destinations.
- Quest performance at 72–90 Hz is unmeasured.
- AR mode may simply overlay the opaque room on passthrough without any thought for that case.

## Top 5 issues

1. **Major: verification evidence is not shown.** *Evidence:* every test appears as "Ran command" followed by a prose claim ("The stereo test passed…", "zero network requests"), with no output, screenshots or test files handed over. *Fix:* include the test-harness output (request count, console error count, IWER session log) and ship the IWER/Playwright check script next to the HTML so the claims can be re-run.
2. **Major: immersive AR, real hand tracking, gaze dwell and frame rate are untested.** *Evidence:* only "mocked input and lifecycle checks" and a VR stereo emulator run are described, and no fps or frame-time figure appears anywhere, yet the answer advertises "Enter AR", pinch, gaze dwell and "Adaptive detail". *Fix:* run an `immersive-ar` session in the emulator, add a frame-time readout or a 72/90 Hz budget test, and label the untested input modes as such in the feature list.
3. **Major: the iPhone and "3D" interpretations are not made explicit.** *Evidence:* iOS gets "screen-based experience" without saying that this is how the done-when is met, a heightfield was chosen silently, and Apple Vision Pro (which does support WebXR in Safari) is not mentioned. *Fix:* state in one line that the phone done-when is met by an in-browser 3D room, mention visionOS Safari support, and briefly justify the heightfield choice or offer a volumetric mode.
4. **Minor: the hosting and handoff path is generic.** *Evidence:* "upload it unchanged to any HTTPS static host", with no command or concrete host, no way to load the file on a Quest or Pico, and "Open file." is left dangling. *Fix:* add a two-line recipe (e.g. a local HTTPS server plus a tunnel, or a named static host) and say how to open the URL in the Quest or Pico browser.
5. **Minor: internal jargon leaks into the user-facing log.** *Evidence:* "using the Library skill", "Fractal, Xr and Compatibility started working", and "Edited 01a1880b-…:exec-…". *Fix:* describe the work streams in plain language and drop the internal identifiers from user-facing narration.

## Strengths

- Platform limits are stated honestly and with sources: iOS Safari, Steam Frame's Chromium status, ARCore dependence, and the secure-context requirement.
- It tested the actual Three.js immersive path in an XR emulator (stereo, controllers, select, exit, camera restore) rather than stopping at desktop rendering.
- Self-review produced real fixes: the pillar-occluded camera, the double-counted double-tap, and the menu blocking the sculpture.
- Robust architecture: a fully offline single file, worker-based fractal computation off the frame loop, and graceful fallbacks for missing workers or denied permissions.
- Rich VR usability: an in-world menu that grip summons, teleport, snap turn, several input modalities, and a fallback non-XR room for phones.

## Verdict

A strong, efficient one-turn delivery. It researched the device landscape, built an offline, worker-backed WebXR experience with sensible fallbacks, and caught several UX defects through its own testing. Its claims are well calibrated, and untested hardware is disclosed. The main weakness is that the verification lives only in narration: AR, hand and gaze input, and headset performance go unevidenced, and the iPhone and "3D" interpretations are never stated outright.
