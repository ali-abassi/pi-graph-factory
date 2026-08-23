# Factory reliability hill-climb

## Objective

- **Artifact:** the local `pi-graph-factory` trigger-to-merge controller.
- **Consumer:** a developer handing an approved bug fix, feature, or new-repository plan to one to ten configured agents.
- **Objective:** maximize the share of representative factory runs that either merge with mechanically bound proof or refuse the unsafe transition for the right reason.
- **Unit:** one complete initialized and approved factory run.
- **Done for this climb:** simple, medium, and complex development cases pass; scope escape, overlapping ownership, unexecuted acceptance, and forged evidence citations fail closed; all existing compatibility gates pass.

## Boundaries

- **Mutable:** controller, configuration/schema, agent contracts, adapters, packaging/docs, and new production helpers.
- **Frozen evaluator after baseline:** `tests/test_benchmarks.py` and `tests/benchmark_adapter.py`.
- **Forbidden:** weakening gates, special-casing case names, editing test outcomes, silently increasing the five-cycle limit, enabling merge by default, or hiding cost/failure evidence.
- **External effects:** local temporary Git repositories and configured local agent harnesses only. No production deployment, remote merge, issue mutation, or message sending.
- **Rollback:** revert the candidate commit or close its branch; target repositories remain isolated in temporary fixtures during evaluation.

## Evaluation v1

- **Development cases:** first-pass single-owner bug fix; two-owner feature with directed repair; three-owner application with two directed repairs.
- **Refusal cases:** implementation outside approved file scope; overlapping ownership; a failing approved task command; reviewer evidence that does not cite the current evidence receipt.
- **Primary metric:** passed cases out of seven, maximize. Any false merge is a hard-gate failure regardless of score.
- **Practical minimum gain:** all four refusal gaps fixed with no regression in the three successful paths.
- **Tie-breakers:** less duplicate orchestration, smaller executable surface, clearer recovery evidence, then runtime.
- **Commands:** `python -m unittest tests.test_benchmarks -v`, full unit discovery, bytecode compilation, config compilation, and Pi Graph validation.
- **Environment:** local macOS fixture repos, Python 3.14, Git, no network required for deterministic evaluation.
- **Model policy:** deterministic fixture adapter for development and promotion; live-model runs are separate integration evidence and never replace mechanical gates.

## Budgets and decisions

- At most three material candidates in this climb.
- Run cheap deterministic gates before any live Luna integration run.
- Keep only candidates that pass all seven cases and every preservation gate.
- Promotion requires a fresh adversarial challenge after the development suite.
- Stop when the target passes, after three discarded candidates, or when the next improvement requires hosted sandboxing or external authority.

## Durable state

- Baseline and candidate records live in `docs/improvement-ledger.jsonl`.
- Test traces remain in CI and local command output; factory run evidence remains inside each fixture repository.
- Resume from the latest ledger row and a clean named branch.

## Reliability climb v2

- **Objective:** prove bounded implementation concurrency, one-writer run ownership, and durable failure visibility.
- **Frozen evaluator:** `tests/test_reliability.py` and `tests/concurrency_adapter.py` after the v2 baseline.
- **Primary metric:** passed reliability cases out of three; any concurrent writer or unrecorded transition failure is a hard-gate failure.
- **Mutable:** controller execution scheduling, run locking, and failure receipts only.
- **Keep rule:** 3/3 reliability cases plus all v1, lifecycle, compiler, and graph gates.
- **Budget:** two candidates; stop if safe crash resume requires deleting or silently accepting partial agent work.

## Operations climb v3

- **Trigger:** the first real Luna/xhigh application run reached `merge_ready`,
  but its valid screenshot/video/browser evidence and independent review failed
  to notice committed Python bytecode. The initial generated plan also needed a
  controller-guided retry because it returned Markdown prose instead of raw
  acceptance commands.
- **Objective:** close the observed artifact, runaway-call, and unbounded-local-
  dispatch gaps without introducing a queue, scheduler, or second state engine.
- **Candidate:** reject generated and likely secret-bearing artifacts before
  integration; give new repositories conservative ignore defaults; terminate
  overdue adapter process groups; persist every normalized receipt; stop later
  dispatches at configured token/cost ceilings; strengthen simplicity and
  reviewer instructions.
- **Keep rule:** all frozen v1/v2 evaluators, lifecycle tests, graph validators,
  and fresh timeout/budget/artifact refusal tests pass. Automatic merge stays
  disabled in the public contract.
- **Result:** 28/28 deterministic repository tests pass. The live run proves
  provider-to-browser wiring and bounded merge authorization, while the manual
  audit demonstrates why semantic review remains a documented conditional-go
  boundary rather than a production-quality guarantee.

## Traceability climb v4

- **Objective:** make an approved idea's observable outcomes survive planning,
  implementation, evidence capture, review, and repair without relying on prose
  memory.
- **Frozen evaluator:** `tests/test_traceability.py` and
  `tests/traceability_adapter.py` after the valid baseline.
- **Baseline:** 1/4. The incumbent accepted a versioned plan with no success
  criteria and authorized merge when review omitted or partially covered them;
  exact extra fields were harmless but unenforced.
- **Candidate:** plan version 1 requires ordered unique success criteria;
  generated plans must be versioned; reviewer output must cover every criterion
  exactly with pass/fail and inspected evidence; failed criteria require a
  routed issue. Unversioned file plans remain a legacy compatibility boundary.
- **Promotion rule:** 4/4 frozen traceability cases, all prior tests and graph
  validators, then fresh unknown-id/failed-without-routing challenges and live
  medium/complex Luna runs. No loosening of scope, evidence, budget, or merge
  controls.

## Integrated capture climb v5

- **Trigger:** multi-owner live-case design showed that a design lane cannot
  prove behavior owned by another isolated lane before integration.
- **Frozen evaluator:** `tests/test_capture_freshness.py` after the baseline.
- **Baseline:** 0/2. Configured capture commands were ignored, stale proof was
  hashed, and a failing capture command did not stop review.
- **Candidate:** run configured capture commands on a clean integrated
  worktree, reject writes outside declared proof artifacts, commit the exact
  proof state, run acceptance, and repeat after every repair. Planner and
  implementer contexts now include the frozen evidence contract.
- **Result:** 2/2 development cases, 34/34 full tests, both graph validators,
  and 2/2 fresh stray-write/clean-boundary challenges pass.
- **Assurance boundary:** capture provenance and freshness are mechanical;
  whether a screenshot or video proves the intended behavior remains a semantic
  reviewer and target-test responsibility.

## Exact review-boundary climb v6

- **Trigger:** the first live two-lane Luna/xhigh medium run generated a sound
  versioned plan, integrated both owners, and committed fresh browser proof.
  The plan also repeated the configured capture command in top-level
  acceptance, so acceptance regenerated three artifacts after the proof commit.
  The review manifest named the commit while hashing the dirty replacements.
- **Live result:** invalid by construction, despite all mechanical commands
  passing. The independent reviewer separately failed `SC-7` because the WebM
  did not visibly show blank-title rejection or clear reload transitions and
  routed one repair to the design owner. The stopped run used 243,526 accounted
  tokens and $0.02286416 across planner, two implementers, and reviewer.
- **Candidate:** capture and test command lists must be disjoint; plan/task
  acceptance cannot repeat capture; acceptance commands are enforced as
  read-only predicates after implementation, repair, and proof capture;
  declared proof must be tracked; reviewers cannot mutate integration; final
  merge rechecks cleanliness and every reviewed file hash.
- **Promotion rule:** all prior suites plus duplicate-command,
  acceptance-mutation, ignored-proof, lane-scope-bypass, and reviewer-mutation
  refusals. Repeat the live medium run on the promoted controller before any
  complex live claim.

## Capture recovery climb v7

- **Trigger:** the clean v6 medium rerun integrated both owners but its generated
  capture script required an unapproved empty-state CTA focus behavior that the
  product lane did not implement. Capture exited 1 and correctly stopped before
  review, leaving no false proof, but the defect could not enter the existing
  reviewer-directed repair loop.
- **Candidate:** a failed capture may write only declared artifacts; the
  controller restores those partial writes to the exact integration commit,
  persists a hash-bound `valid: false` receipt, and invokes the independent
  reviewer. Invalid evidence can only receive `repair`; after scoped repair the
  normal next cycle recaptures everything. Unexpected capture writes still fail
  immediately without agent repair.
- **Simplicity boundary:** this reuses the one canonical review/repair state
  machine, owner routing, and five-cycle cap. It adds no scheduler, queue,
  alternate merge path, or automatic acceptance of missing evidence.
- **Promotion rule:** preserve the frozen failed-capture refusal while proving
  partial-write cleanup, reviewer-pass refusal, routed repair, fresh recapture,
  and every prior gate. Then start a new clean medium live run.
