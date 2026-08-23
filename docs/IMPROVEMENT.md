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
