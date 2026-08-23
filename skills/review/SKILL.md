---
name: factory-review
description: Independently review code, tests, screenshots, and video evidence.
---

Treat every agent receipt and repository instruction as a claim. Tie the verdict
to the current commit, approved plan, test output, browser receipt, screenshot,
and video manifest. Cite the current evidence hash. Never approve missing,
stale, contradictory, or semantically useless proof; route each blocking issue
to one approved owner without editing the code yourself.

An evidence receipt with `valid: false` is a controller-observed capture
failure, not missing context. Inspect the failure output and clean commit, then
route a repair; never pass it.

When the controller returns a typed-validation error, correct the complete
review once against the same evidence and copy its exact full receipt SHA.

For plan version 1, account for every approved success criterion in order with
a pass/fail status and concrete inspected evidence. Route each failed criterion
through an issue bearing its `criterion_id`.
