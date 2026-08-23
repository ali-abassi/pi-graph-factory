# Launch review

## Decision

**Conditional go for trusted local trials. No-go for untrusted or unattended
production execution.**

The factory now has strong local merge authorization: exact plan approval,
isolated owner worktrees, Git-derived scope, executed acceptance, commit-bound
evidence, independent review, bounded repair, one-writer locking, and durable
caught failures. Those controls materially reduce false completion and unsafe
merge.

They do not sandbox agent processes, guarantee semantic visual judgment, impose
hard provider-side spend caps, or automatically recover dirty partial work
after abrupt death. Those are the conditions separating a trustworthy local
alpha from an unattended production service.

## System model

- **Entry points:** `init`, `plan`, `answer`, `approve`, `run`, and `status`.
- **Assets:** source repositories, credentials available to local processes,
  approved plan and merge authority, proof artifacts, provider quota and spend.
- **Actors:** operator, planner, one to ten implementers, independent reviewer,
  local harness/provider, and repository content that may be adversarial.
- **Sources of truth:** frozen config and plan hashes, Git commits and staged
  paths, controller-run command results, evidence manifest, append-only events,
  and final receipt.
- **Trust boundaries:** agents and repository data are untrusted; deterministic
  controller gates authorize transitions. The invoking OS account remains a
  broad trusted boundary.

## Critical invariants

1. No merge without exact-plan approval and a clean current review.
2. No agent change outside its approved owner scope.
3. No acceptance or proof claim without controller-observed evidence.
4. No stale evidence after a repair.
5. No more than one state-writing controller and five review attempts.
6. No later dispatch after a configured local usage ceiling is observed.
7. No claim of sandboxing, automatic crash recovery, hard provider spend
   enforcement, or universal visual quality.

## Evidence

- 28 deterministic repository tests across simple, medium, complex, refusal,
  lifecycle, concurrency, and graph cases.
- 4/4 fresh adversarial promotion cases.
- SIGKILL holdout proving lock release, contiguous events, and fail-closed retry.
- A live Luna/xhigh browser application run reached `merge_ready` with four
  passing target tests, screenshot, WebM, and a clean browser receipt. Manual
  audit caught committed bytecode that the model reviewer missed; the promoted
  controller now rejects that artifact class mechanically.
- Pi Graph Core v0.1.0 and Pi Graph v0.3.0 validation of the 24-node topology.
- Full risk register: [`risk-register.json`](risk-register.json).

## Next conditions

The next high-value work is explicit inspect-and-resume for interrupted
worktrees and a frozen Luna-driven application corpus with stronger browser or
native proof scoring. Sandboxing and provider-side budgets are deployment
adapters, not reasons to inflate the core controller.
