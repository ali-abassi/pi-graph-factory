---
name: factory-project-verification
description: Create or maintain a project-local driver that proves real user behavior and preserves evidence.
---

# Project verification

For a new executable product, or an existing product without a credible way to
drive the changed surface, build the verification lever before calling the work
complete. Reuse an existing Playwright, XCUITest, CLI, HTTP, or platform harness
when one is honest; do not add a second driver for ceremony.

Ground the driver in five facts from the repository:

- **Surface:** what the user actually touches.
- **Launch:** the repository's real start/build command and observable readiness.
- **Drive:** stable user-facing handles, commands, routes, or accessibility ids.
- **Observe:** behavior, side effects, logs, screenshots, video, and exit status.
- **Isolate:** ports, profiles, simulator ids, data directories, and exact cleanup.

The resulting repository-local script or documented command must provide:

1. a read-only doctor check before driving;
2. launch/readiness and exact teardown for only the process or simulator it owns;
3. actions through the production user seam, not internal setters or test-only
   shortcuts;
4. evidence of both the action and resulting state, plus material side effects;
5. deterministic artifact paths and semantic validation of each artifact;
6. cleanup that preserves proof and also runs after failed attempts; and
7. at least one complete execution of its own instructions before handoff.

Update `FEATURE_MAP.md` when the changed user-facing capability is missing or
materially different. A blank screenshot, corrupt video, stale build, healthy
process with a wedged UI, or self-reported receipt is not proof. If the matching
surface cannot be driven, say exactly what is unavailable and keep the result
blocked or inconclusive.

For an interaction-video claim, preserve the real screen-recording command and
the user-drive command in the receipt. Sample multiple points on the timeline
and confirm the approved controls, transitions, and resulting states are visibly
present. Never build an MP4 from screenshots or substitute unrelated motion to
satisfy a video path.
