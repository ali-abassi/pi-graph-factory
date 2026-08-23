# Changelog

All notable changes to Pi Graph Factory are documented here.

## Unreleased

### Added

- Configured `plan --generate` with durable typed plan revisions and planner receipts.
- Versioned success criteria with exact independent-review coverage and routed
  failures.
- Concurrent isolated implementation lanes for active approved owners.
- One-writer controller locking and durable caught-failure receipts.
- Per-agent process-group timeouts, durable normalized receipts, and aggregate
  token/cost dispatch ceilings.
- Post-integration evidence capture commands with declared-output confinement,
  proof commits, and automatic recapture after every repair.
- Simple, medium, complex, adversarial, and concurrency benchmark suites.
- Public security, contribution, improvement, and release documentation.

### Changed

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

### Security

- Overlapping owner globs and out-of-scope implementation or repair changes are rejected.
- Failed controller transitions make `status` fail closed.
- Generated caches, compiled bytecode, dependency directories, and likely
  secret-bearing `.env` files are rejected before integration.
- Automatic merge remains disabled by default.
