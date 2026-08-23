# Launch review

## Decision

**Go for trusted local and Railway-hosted trials. Conditional go for configured
delivery. No-go for hostile-code execution or universal unattended production.**

The factory now has strong local merge authorization: commit-aware repository
intelligence, independently judged generated plans, exact plan approval,
isolated owner worktrees, Git-derived scope, executed acceptance, commit-bound
evidence, independent implementation review, bounded repair, one-writer
locking, and durable caught failures. Those controls materially reduce false
completion and unsafe merge.

The runtime now also resumes validated lane, integration, capture, review,
repair, and post-fast-forward checkpoints; selects visual proof only when the
approved plan needs it; and can explicitly deploy, health-check, and attempt a
configured rollback. It does not sandbox hostile code, guarantee semantic
visual judgment, impose provider-side spend caps, or make arbitrary external
commands exactly-once across machine death.

## System model

- **Entry points:** `init`, `plan`, `answer`, `approve`, `run`, `inspect`,
  `resume`, `deliver`, and `status`.
- **Assets:** source repositories, generated repository maps, credentials
  available to local processes, approved plan and merge authority, proof
  artifacts, provider quota and spend.
- **Actors:** operator, planner, independent plan judge, one to ten implementers,
  independent implementation reviewer, local harness/provider, and repository
  content that may be adversarial.
- **Sources of truth:** frozen config and plan hashes, Git commits and staged
  paths, controller-run command results, evidence manifest, append-only events,
  and final receipt.
- **Trust boundaries:** agents and repository data are untrusted; deterministic
  controller gates authorize transitions. The invoking OS account remains a
  broad trusted boundary.

## Critical invariants

1. No merge without exact-plan approval and a clean current review.
2. No generated plan approval unless an independently scored judgment clears
   the configured threshold; the controller recomputes the weighted score.
3. No agent change outside its approved owner scope.
4. No acceptance or proof claim without controller-observed evidence.
5. No stale evidence after a repair.
6. No more than one state-writing controller, three plan-quality cycles, and
   five implementation review attempts.
7. No later dispatch after an explicitly configured local usage ceiling is
   observed; token and cost ceilings may be disabled for subscription sessions.
8. Recovery accepts only known process identities, owner scopes, commits,
   receipts, and current evidence; ambiguous state fails closed.
9. No claim of hostile-code sandboxing, exactly-once external delivery, hard
   provider spend enforcement, or universal visual quality.

## Evidence

- 81 deterministic repository tests across simple, medium, complex, refusal,
  lifecycle, concurrency, and graph cases.
- Graphify tests prove no-code deferral, first indexing, clean ignored output,
  same-commit reuse, refresh after a new commit, semantic-model dispatch,
  credential non-persistence, and explicit AST fallback.
- A live DeepSeek V4 Flash extraction produced a usable 537-node, 1,195-edge
  map. Semantic enrichment is an approved-provider boundary, not a claim that
  repository content remains local; the default falls back to AST-only when it
  is unavailable.
- Planning tests prove a low 8.0 judgment returns to the planner, a later 9.0
  judgment advances, missing project memory is assigned, and a forged overall
  score is refused.
- Controller-death coverage includes a live held lane, committed repair
  reconstruction, and the narrow state-save window after a reviewed
  fast-forward reaches the target branch.
- `evidence.policy: plan` requires the approved plan to choose tests or visual
  proof. Test-only work skips ceremonial screenshots/video; visual artifacts
  remain hash-bound to the integrated commit.
- Optional delivery is deliberately separate from merge and records deploy,
  production-health, and rollback command receipts.
- Versioned approved outcomes must receive exact independent-review coverage
  with concrete inspected evidence; failed outcomes require routed ownership.
- Visual proof is regenerated on the integrated commit and after every repair;
  capture commands may write only declared tracked artifacts. Acceptance and
  review must leave that commit unchanged.
- 4/4 fresh adversarial promotion cases.
- SIGKILL holdout proving lock release, contiguous events, and fail-closed retry.
- A live Luna/xhigh browser application run reached `merge_ready` with four
  passing target tests, screenshot, WebM, and a clean browser receipt. Manual
  audit caught committed bytecode that the model reviewer missed; the promoted
  controller now rejects that artifact class mechanically.
- A live two-lane Luna/xhigh run exposed a duplicated capture command that
  dirtied proof after its commit. The run is explicitly invalid; the controller
  now rejects capture/acceptance overlap and any acceptance/reviewer mutation
  before review. Its independent reviewer also rejected a semantically weak
  video and routed the failed criterion back to design.
- A fresh fixed-controller medium run then stopped on a genuine generated
  capture defect before review. Failed capture is now cleaned back to the exact
  integration commit, represented by a hash-bound invalid receipt, and forced
  through independent review/repair/recapture inside the existing cycle budget.
- The first three-lane complex run exercised that invalid-capture path, then
  exposed a one-character evidence-hash transcription error from the reviewer.
  Review protocol validation now gets one durable correction attempt; a second
  malformed response fails closed.
- A clean two-lane Luna/xhigh medium run reached `merge_ready` in one cycle with
  12/12 reviewed success criteria, six passing target tests, clean desktop and
  mobile screenshots, and a readable 36.2-second WebM. It used 240,052
  accounted tokens and $0.01878568; automatic merge was disabled and target
  `main` remained untouched.
- Later three-lane and existing-repository bug-fix runs produced valid
  commit-bound screenshots/video and exposed three additional protocol gaps:
  issue ownership was not bound to exact files, fenced planner JSON stopped at
  the adapter, and repair receipts omitted `addressed` because the public prompt
  did not specify it. The promoted candidate binds issue target files to owner
  scopes, normalizes one JSON fence with a two-attempt planner bound, and gives
  repair receipts one read-only fingerprinted correction. The final live
  bug-fix run still stopped after two invalid repair receipts; it is refusal
  evidence, not a `merge_ready` claim.
- Pi Graph Core v0.1.0 and Pi Graph v0.3.0 validation of the 26-node topology.
- Full risk register: [`risk-register.json`](risk-register.json).

## Remaining conditions

The next high-value work is the user-observed step-by-step complex run: inspect
every Graphify receipt, planner input/output, plan judgment, lane
context/receipt, integrated check, proof, review, repair, merge, and delivery
receipt against a frozen application corpus. Those approved/rejected plans
should become the first human-rated calibration set for `plan-quality-v1`.
Railway Cloud Agents provide a persistent off-laptop VM, but their shared
personal disk and credentials are still a trusted environment.

External deploy commands need project-specific idempotency and rollback. A VM
dying after a provider accepted a deploy but before the local receipt was saved
cannot be resolved generically. Agent-created background daemons outside the
recorded harness process group also remain an execution-environment concern.
