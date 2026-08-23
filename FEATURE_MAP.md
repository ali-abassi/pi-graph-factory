# Pi Graph Factory feature map

This map records the product capabilities that exist today. `VISION.md` explains
where the product is going; the factory's approved plan remains authoritative
for any individual run.

## Intake and planning

- Initialize durable runs for existing repositories or create a new Git repository.
- Select direct, interactive, or autonomous intake without forking the downstream
  lifecycle.
- Preserve human-led goal briefs and autonomous self-grill briefs/decision ledgers
  with readiness and content hashes in the run ledger.
- Reject autonomous intake with missing decision coverage, unsafe low-confidence
  assumptions, or unresolved human-only decisions.
- Store the request, frozen factory contract, base commit, target branch, and run ledger.
- Build or refresh ignored local Graphify repository intelligence when code exists.
- Defer Graphify for a code-free new project, then create it after implementation.
- Read `VISION.md` and `FEATURE_MAP.md` as durable project decision context.
- Generate versioned plans with research, assumptions, success criteria, ownership,
  executable acceptance, proportional proof, risks, and genuinely blocking questions.
- Independently judge generated plans with the `plan-quality-v1` rubric, revise below
  8.5/10, and stop after three unsuccessful quality cycles.
- Require explicit SHA-256 approval of the exact final plan.

## Implementation and integration

- Dispatch one to ten configured Pi, Claude Code, or Codex implementers concurrently.
- Isolate initial owner work in Git branches and worktrees.
- Reject overlapping planned scopes and actual out-of-scope or unsafe staged files.
- Execute approved task checks and integrate passing lane commits deterministically.
- Apply a smallest-complete-change policy through implementer instructions and skills.
- Apply the Ponytail solution ladder in product and design lanes across Pi,
  Claude Code, and Codex harnesses.

## Proof and review

- Select test-only or visual proof according to the approved plan.
- Capture declared screenshots, video, and browser artifacts on the integrated commit.
- Bind proof hashes to the current commit and approved plan.
- Require an independent read-only review to account for every success criterion.
- Review the integrated diff for concrete deletable abstractions, wrappers,
  dependencies, and speculative flexibility without weakening correctness or safety.
- Route concrete failures to the named owner and exact approved target files.
- Recheck, recapture, and rereview repairs for at most five total review cycles.

## Merge, delivery, and operations

- Issue a merge-authorizing receipt or fast-forward the unchanged target when enabled.
- Keep automatic merge and delivery disabled by default.
- Run an explicit configured deploy, health check, and rollback attempt after merge.
- Inspect active operations, receipts, contexts, events, worktrees, and proof artifacts.
- Resume only validated checkpoints; fail closed on ambiguous state.
- Compile an inspectable Pi Graph Core policy topology for Studio/graph visualization.

## Deliberate gaps

- Issue/webhook ingestion and a hosted clarification interface are external adapters.
- Railway is documented as a persistent trusted runner, not provisioned by this repo.
- The plan judge has deterministic contract tests but still needs calibration against a
  user-reviewed corpus of real plans.
- Hostile-code sandboxing, universal semantic review, automatic conflict resolution,
  provider-side budget enforcement, and exactly-once deployment are not claimed.
