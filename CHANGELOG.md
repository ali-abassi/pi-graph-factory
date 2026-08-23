# Changelog

All notable changes to Pi Graph Factory are documented here.

## Unreleased

### Added

- Commit-aware Graphify repository intelligence before generated planning, with
  automatic setup, ignored local output, no-code deferral, and post-implementation refresh.
- `VISION.md` and `FEATURE_MAP.md` project memory, including safe new-repository
  initialization and generated-plan ownership for missing files.
- Evidence-backed plan research and assumptions plus an independent anchored
  plan judge. Scores below 8.5/10 return to the planner for at most three cycles.
- A project-level `FEATURE_MAP.md` and graph-first planner/implementer guidance.
- Configured `plan --generate` with durable typed plan revisions and planner receipts.
- Versioned success criteria with exact independent-review coverage and routed
  failures.
- Concurrent isolated implementation lanes for active approved owners.
- One-writer controller locking and durable caught-failure receipts.
- Per-agent process-group timeouts, durable normalized receipts, and aggregate
  token/cost dispatch ceilings.
- Post-integration evidence capture commands with declared-output confinement,
  proof commits, and automatic recapture after every repair.
- Evidence-failure receipts that let independent review route capture defects
  through the existing bounded repair loop.
- One durable controller-guided retry for malformed reviewer output against the
  same evidence and cycle.
- Simple, medium, complex, adversarial, and concurrency benchmark suites.
- Public security, contribution, improvement, and release documentation.
- A product-level `VISION.md` and Railway Cloud Agent operating guide.
- `inspect` and checkpoint-validating `resume` commands for interrupted runs.
- Plan-selected test or visual proof, with media reserved for UI and interaction
  changes.
- Explicit post-merge delivery with deploy, health, rollback, and final receipt
  recording.

### Changed

- Questions are now reserved for material choices that repository evidence,
  project memory, and a safe reversible assumption cannot resolve.
- The compiled policy graph now begins with repository intelligence and includes
  an independent pre-implementation plan-quality gate.
- Git is now the source of truth for changed files; agent claims must match it.
- Approved task and integrated acceptance commands now execute mechanically.
- Reviewer approval must cite the current evidence manifest hash.
- Evidence paths are repository-confined and symlink escapes fail closed.
- The compiled graph now has one guarded merge exit per review and explicit
  final human escalation.
- Generated `steps.yaml` is no longer committed.
- New repositories start with conservative ignores for local factory state,
  environment files, caches, bytecode, virtual environments, and dependencies.
- Default screenshot, video, and browser-receipt paths now use the tracked
  `evidence/factory/` directory so proof survives isolated-lane integration.
- Acceptance commands are enforced as read-only predicates and cannot repeat
  configured evidence capture commands.
- Role timeouts and termination grace are configurable; timeouts may be
  disabled. Token and dollar ceilings are optional and disabled by default for
  subscription-backed harnesses.
- Interrupted lanes, declared capture writes, owner-scoped repairs, committed
  repair checkpoints, and a reviewed fast-forward can resume without restarting
  the factory.

### Security

- Overlapping owner globs and out-of-scope implementation or repair changes are rejected.
- Failed controller transitions make `status` fail closed.
- Generated caches, compiled bytecode, dependency directories, and likely
  secret-bearing `.env` files are rejected before integration.
- Ignored/untracked evidence, post-capture acceptance writes, and reviewer
  mutations are rejected before merge authorization.
- Automatic merge remains disabled by default.
- Resume refuses unknown processes, unrecognized commits, undeclared capture
  writes, out-of-scope partial repairs, and target-branch drift.
- Delivery remains explicit and fails closed unless the applied merge, clean
  repository, deploy result, and production health result match the frozen
  contract.
