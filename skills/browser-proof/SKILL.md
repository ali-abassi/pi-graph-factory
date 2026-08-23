---
name: factory-browser-proof
description: Capture real screenshot, video, interaction, console, and network proof for a local web change.
---

Use the target project's capture command when one exists. Otherwise create one
small repeatable script under the approved scope. Start the local app on
`127.0.0.1`, use a unique named `agent-browser` session, and close both browser
and server on exit.

The controller runs configured capture commands after all implementation lanes
integrate and again after every repair. Write only the declared screenshot,
video, and receipt paths; stray capture outputs fail the transition.

For each declared flow:

1. open the local URL with content boundaries enabled;
2. take an interactive snapshot and verify the expected controls exist;
3. start recording before interaction;
4. perform the real clicks/typing and re-snapshot after every page change;
5. assert the visible result, capture the declared screenshot, and stop video;
6. inspect console and failed network requests; and
7. write a JSON browser receipt containing the URL, viewport, observed result,
   console errors, network errors, screenshot path, and video path.

Never manufacture image or video bytes. A file existing is not proof that the
flow worked. Prefer stable roles, labels, or test ids over brittle CSS selectors.
Use a mobile viewport too when the approved plan requires it.
