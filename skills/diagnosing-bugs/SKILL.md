---
name: factory-diagnosing-bugs
description: Diagnose defect tasks with a tight reproduction loop and a regression test at the real seam.
---

Use this only for a bug, regression, failing test, incident, or unexplained
behavior. Establish a fast red-capable feedback loop before changing production
code. Reproduce the reported behavior, minimize the case, and distinguish the
observed facts from theories.

When the cause is not immediately proven, rank three to five falsifiable
hypotheses. Test one discriminating variable at a time. Temporary instrumentation
must be clearly tagged, must not expose secrets or personal data, and must be
removed before the final receipt.

Once the cause is proven, add the smallest regression test at the public seam
that should have prevented it. Observe that test fail for the defect, make the
minimum correction, and then run both the test and the original reproduction.
Do not leave exploratory patches, debug output, or a test of a private helper in
place of proof of the reported behavior.

Adapted from Matt Pocock's MIT-licensed diagnosing-bugs skill:
https://github.com/mattpocock/skills/blob/main/skills/engineering/diagnosing-bugs/SKILL.md
