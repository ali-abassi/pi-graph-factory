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

## Reviewer protocol recovery climb v8

- **Trigger:** the first three-lane complex run produced a clean invalid-capture
  receipt and an otherwise correct reviewer repair decision, but Luna copied 63
  of the 64 evidence-hash characters. Exact citation validation correctly
  stopped routing, and the run could not continue.
- **Candidate:** give each review cycle at most two typed-output attempts against
  the identical commit and evidence. Persist both normalized receipts and an
  event carrying the controller validation error; feed the first invalid output
  and exact error back once. Reviewer mutation, timeouts, and usage limits still
  fail immediately rather than retrying.
- **Simplicity boundary:** this mirrors the existing two-attempt planner
  validation pattern. It does not add review votes, relax exact hashes, consume
  a repair cycle, or permit a third attempt.
- **Promotion rule:** one malformed citation followed by a corrected complete
  review succeeds; two malformed attempts fail closed; all prior tests and
  security/graph gates pass; then repeat the clean complex live case.

## Routing and adapter protocol climb v9

- **Trigger:** the v8 complex reviewer correctly identified a frontend/backend
  contract mismatch but routed it to the backend despite naming `web/app.js` as
  the defective file. A later high-reasoning planner returned a complete plan
  inside a JSON fence, which the provider adapter discarded before the
  controller's existing correction path could run.
- **Candidate:** every version 1 issue names exact repository-relative
  `target_files`; each must match the routed owner's approved patterns. Pi model
  output becomes a usage-bearing typed invalid receipt when it is not JSON; one
  JSON code fence is normalized, arbitrary surrounding prose remains invalid,
  and planner validation keeps its existing two-attempt ceiling.
- **Result:** the frozen wrong-owner and missing-target challenges improved from
  0/2 to 2/2. The live fenced plan then completed on its first controller
  attempt, preserved exact approval, and launched three correctly isolated
  lanes.

## Repair receipt protocol climb v10

- **Trigger:** a complex release repair produced valid screenshots, WebM, and
  an all-true browser receipt, but its typed response omitted `addressed`; the
  controller correctly refused to infer accountability. The public implementer
  prompt showed only the initial implementation shape and never documented the
  field the controller required.
- **Candidate:** a structurally passing repair with wrong `addressed` ids gets
  one receipt-only correction using read tools. The already-produced staged
  diff is scope-validated and fingerprinted before that call; any file mutation
  or second invalid receipt fails closed. The implementer instructions now give
  exact initial-repair and receipt-correction shapes.
- **Result:** the deterministic recovery and mutation challenges both pass; all
  54 repository tests pass. A focused existing-repository bug-fix run integrated
  strict backend/frontend validation and generated valid commit-bound proof.
  Its reviewer then found whitespace validation drift and incomplete network
  history coverage. The repair fixed the frontend files but repeated the
  prompt-driven receipt omission twice, so the pre-prompt-fix live run stopped
  safely. No complex live `merge_ready` claim is made.
- **Simplicity boundary:** no resume engine, queue, extra review vote, inferred
  issue completion, or relaxed evidence rule was added. Interrupted live runs
  remain inspectable refusals and automatic merge remains off.

## Factory runtime climb v11

- **Trigger:** operator review identified four mismatches with the intended
  product: interrupted runs could strand useful work, subscription-backed
  harnesses inherited arbitrary local usage ceilings, media proof was required
  even for tiny non-UI changes, and a clean merge had no explicit delivery
  state.
- **Candidate:** add a concise operator `inspect` view and validated `resume`;
  reconstruct committed lanes and repairs from Git plus durable receipts;
  continue owner-scoped partial repairs; clean only declared interrupted capture
  writes; recover the narrow reviewed-fast-forward/state-save window; select
  tests or visual proof in the approved plan; configure or disable role and
  command timeouts; disable token/dollar ceilings by default; and add an
  explicit deploy/health/rollback contract.
- **Execution boundary:** document Railway Cloud Agents as a persistent
  off-laptop wrapper around the one canonical controller. Do not add a second
  queue or workflow state machine, and do not call a credentialed personal VM a
  hostile-code sandbox.
- **Promotion rule:** all prior evaluators plus active-lane SIGKILL recovery,
  committed-repair reconstruction, post-fast-forward recovery, test-only proof,
  optional subscription limits, configurable timeouts, and health-gated
  delivery must pass. Both Pi Graph validators, lint, bytecode compilation,
  dependency audit, secret scan, and Bandit medium/high remain required.
- **Assurance boundary:** local Git transitions resume from mechanically known
  checkpoints. Arbitrary external provider effects and background daemons
  outside the recorded process group are not transactionally exactly-once.

## Repository-grounded planning climb v12

- **Trigger:** planning previously began with broad repository inspection, had
  no durable project vision/feature context, and could advance a syntactically
  valid but weak plan directly to operator approval. New projects also had no
  explicit lifecycle for gaining repository intelligence after code appeared.
- **Candidate:** create or refresh a local ignored Graphify map when tracked code
  exists; reuse it only at the exact source commit; rebuild corrupt or stale
  caches; defer cleanly for a code-free project and retry after implementation.
  Feed capped `VISION.md` and `FEATURE_MAP.md` content to a graph-first planner,
  require evidence-backed research and explicit assumptions, and assign missing
  project-memory files as implementation work.
- **Quality gate:** send each generated plan to a fresh independent judge using
  anchored grounding, coverage, feasibility, minimality, and alignment scores.
  Recompute the weighted score mechanically, require 8.5/10, and return precise
  rubric-linked advice to the planner for at most three quality cycles. Exact
  operator approval remains mandatory after the judge passes.
- **Result:** 73/73 repository tests pass. Deterministic cases prove new-project
  deferral-to-ready, first indexing, cache reuse, corrupt/stale refresh, ignored
  graph output, missing project-memory restoration, low-score revision, forged
  score refusal, and the unchanged implementation/review/merge safety suite.
  The 26-node policy graph passes both validators; Ruff, bytecode compilation,
  dependency audit, Bandit medium/high, and Gitleaks also pass.
- **Simplicity boundary:** Graphify remains an ignored index rather than a
  second workflow engine or committed dependency. The existing controller owns
  the one planning loop. No vector database, agent memory service, judge voting,
  or extra scheduler was added.
- **Assurance boundary:** deterministic control flow and rubric arithmetic are
  proven; semantic plan scoring is not yet calibrated against a frozen
  human-rated corpus. The next step-by-step live runs become that corpus.
