# Changelog

All notable changes to Pi Graph Factory are documented here.

## Unreleased

### Added

- Dedicated `prompt` and `optimization` owners. Prompt work uses a production
  runtime/trust/schema/host/evaluation contract with six required case kinds.
  Optimization uses an AutoAgent-shaped but finite controller-owned loop:
  baseline, one isolated mutation per dispatch, controller scoring and gates,
  keep/discard, absolute plateau/time bounds, and one run-level promotion.
  Prompt commands return controller-parsed case receipts; optimization repair
  requires a newly approved evaluation version instead of reusing promotion.
- A dedicated `copy` implementation specialist plus a portable adaptation of
  Ali Abassi's `evil-genius-copywriter` discipline for product, UX, website,
  repository, lifecycle, and promotional messaging. Product/UI owners share
  its sharp, evidence-bound copy capability for text embedded in their files;
  review verifies claims, constraints, sentence integrity, and reader agency.
- Optional DeepSeek V4 Flash semantic enrichment for Graphify repository docs
  and community labels, with an in-memory Pi credential bridge, profile-aware
  caching, explicit AST fallback, and secret non-persistence tests.
- Conditional public-seam TDD and reproduce-diagnose-regress skills for
  implementation lanes, plus two-axis independent review.
- A documented placement decision for triage, architecture improvement,
  docs-enabled grilling, specs, tickets, implementation, and wayfinding skills.
- One evidence-bound clear-prose skill synthesized from ten reviewed anti-slop
  sources and loaded into every existing workflow role without a new stage.
- Direct, interactive, and autonomous intake modes with durable brief provenance,
  structured self-grill validation, and planner handoff.
- Ponytail-derived implementation and review skills, including skill prompt
  loading for Claude Code and Codex harnesses.
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

- Generated plans cannot hide a weak critical dimension behind a strong
  weighted average, and deploy/health/rollback commands are rejected from
  pre-merge acceptance so delivery is always tested against the reviewed
  merge.
- Claude Code lanes receive their configured tool allowlist. Typed prompt and
  optimization receipts are parsed from stdout independently of diagnostic
  stderr, then prompt receipts are revalidated on the integrated commit rather
  than trusted from an isolated lane.
- Reviewer repair receipts carry exact issue ids, prompt evaluations bind to a
  stable runtime id, and proportional proof cannot be satisfied by placeholder
  screenshot or video files.
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
