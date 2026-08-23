---
name: factory-tdd
description: Prove changed public behavior one vertical slice at a time at an approved test seam.
---

Apply this discipline when an approved task changes executable behavior. The
approved plan is expected to identify the observable behavior and credible test
seam; exact plan approval is the agreement on that seam. If the seam is missing
or cannot demonstrate the behavior without coupling to implementation details,
stop as blocked rather than inventing a broad test architecture.

For each slice:

1. Add or change the smallest test that expresses one public behavior.
2. Run it before the production change and observe the relevant failure.
3. Write the minimum code that makes that test pass.
4. Re-run the focused test, then the approved wider checks.
5. Refactor only after the behavior is green and only when the result is simpler.

Prefer vertical behavior slices over tests for every internal layer. Do not test
private functions merely because they are easy to reach. Mock only boundaries
the project does not own, such as networks, clocks, filesystems, or third-party
services; prefer real project code elsewhere. Documentation-only, metadata-only,
and generated-artifact tasks do not require ceremonial test-first work, but they
still run their approved predicates.

Adapted from Matt Pocock's MIT-licensed engineering TDD skill:
https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md
