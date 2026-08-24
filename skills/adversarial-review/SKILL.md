---
name: factory-adversarial-review
description: Attack consequential product, system, and proof assumptions before merge.
---

# Proportional adversarial review

Use this inside the existing independent review when failure, abuse, unsafe
autonomy, weak evidence, or launch risk could change the merge decision. Do not
create a second review lifecycle and do not burden a tiny documentation change
with theatrical edge cases.

1. Model the reviewed surface: intended outcome, users and affected non-users,
   assets, permissions, entry points, trust boundaries, sources of truth,
   invariants, recovery path, and explicit untested boundary.
2. Invert the happy path. Select the few plausible failure chains with the
   highest consequence: precondition -> trigger -> failed control -> effect ->
   detection -> recovery. Consider malformed/stale/duplicate state, partial
   completion, retry or concurrency, dependency failure, resource exhaustion,
   operator error, prompt injection, fabricated completion/evidence, and a green
   health signal while the user outcome is broken.
3. Prefer safe read-only inspection and reversible local tests inside the
   approved worktree or Simulator. Never attack production, use credentials,
   spend money, access real user data, or expand permissions without explicit
   authority.
4. A consequential finding must cite observed evidence, the violated approved
   criterion, exact owned target files, and a falsifiable repair check. Do not
   block on low-value hypotheticals or cosmetic preference.
5. Never call the result safe merely because no issue was found. State what was
   tested, what passed, remaining uncertainty, and the assurance boundary.

No unresolved failure outside an approved success criterion may become a repair
issue in the version-1 review protocol. If it is material but out of scope,
record it only in private review evidence for later planning; do not smuggle it
into the current merge gate.
