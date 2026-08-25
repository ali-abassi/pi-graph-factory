# Factory efficiency improvement contract

## Objective

- Artifact: Pi Graph Factory's request-to-merge controller and default role contract.
- Consumer or real-world task: A developer who could otherwise hand the same request to a strong Codex `/goal` and let one agent work autonomously.
- Objective: Make the factory earn its overhead by adding unattended reliability, proportional proof, recoverability, and an independent finish-line check while staying close to a direct agent's latency on small work.
- Unit of improvement: One clean `factory start` run from frozen intake to guarded local merge.
- Definition of done: The small non-visual path needs no more than three successful model calls—planner, one implementation owner, and independent reviewer—while all existing correctness, scope, evidence, recovery, and merge gates pass. Medium visual and consequential work must retain the full plan-judge/specialist path.
- Non-goals: Removing durable ledgers, allowing unreviewed merges, weakening evidence, special-casing Pocket Queue, replacing the controller with a second workflow engine, or claiming an unmeasured win over `/goal`.

## Boundaries

- Mutable surface: `scripts/factory.py`, `schemas/factory.schema.json`, `factory.yaml`, `agents/planner.md`, focused controller tests, and user-facing documentation.
- Forbidden surface: Archived v18 requests/evaluators/results; target acceptance tests; final-review, Git-scope, evidence, secret, clean-tree, merge, and recovery gates; model-reported metric parsing.
- Repository or system instructions: `AGENTS.md`, `VISION.md`, `FEATURE_MAP.md`, and the public controller contracts remain authoritative.
- Authorized external effects: Read archived local evaluation traces; run deterministic local tests; later run a fresh local target evaluation with configured subscription-backed agents. No deploy, publish, push of a target project, or production mutation.
- Rollback path: Revert the focused candidate commit or configure routing mode `full`; archived traces remain immutable.

## Evaluation v1

- Development cases: Archived Pocket Queue small case plus deterministic synthetic plans at every fast-path boundary.
- Preservation gates: Complete factory unit suite, Ruff, Python compilation, factory config/schema validation, Pi Graph compilation/validation, secret scan, and `git diff --check`.
- Promotion holdout or fresh challenge source: A fresh small non-visual repo request not used to tune the route, followed by the existing Atlas After Dark medium visual case as a downgrade canary. Monster Truck iOS remains deep-path evidence, not a fast-path tuning case.
- Primary metric and direction: Successful model calls before merge, minimize from the archived baseline of 5 to at most 3.
- Practical minimum gain: At least 2 fewer calls and no new human checkpoint, retry, repair cycle, failed hard gate, or loss of independent final review.
- Tie-breakers: Lower wall time and tokens, then smaller controller diff and fewer new concepts.
- Evaluator command or procedure: Archived `evaluate_small.py` result for baseline; focused routing tests for candidate development; unchanged archived evaluator on the fresh target for promotion.
- Artifact hash/version: incumbent `3993be9fe9f2988738e77099e2bdb31181c0d1fc` before this dashboard/efficiency work; candidate recorded after implementation.
- Evaluator hash/version: `evaluate_small.py` SHA-256 `f9fda8e698075078ded9a3402ce07b99669b25a83e8c8960bf13a5df0d9bea05`, live evaluation schema v18.
- Data hash/version: `small-pocket-queue.md` SHA-256 `066f59f4c6f4b9fc3c5a6cddfc71bf9375a17b3b9871ecbe05b053cd9abb19c3`.
- Comparison-arm identity: Archived full-path baseline at v18 versus adaptive fast-path candidate; identical final implementation/review/merge gates.
- Model/provider/thinking fingerprint: Baseline Pi `openai-codex/gpt-5.6-luna` xhigh for planner, implementation, judge, and review. Promotion must pin one declared model profile for both arms; deterministic development tests invoke no provider.
- Tool-set fingerprint: Planner read/research tools; implementation read/edit/write/bash; reviewer read-only inspection plus bash; unchanged controller tools.
- Budget fingerprint: Baseline five calls, 102,209 total tokens, 1,038.218 seconds; candidate target three calls, no arbitrary subscription token/cost cap, existing role timeouts.
- Environment fingerprint: Local macOS Git/Python controller; exact dependency versions remain frozen by the repository environment.
- Wall-time, token, and cost accounting: Read normalized receipts and run timestamps; unknown subscription usage stays unknown and cannot count as a win.
- Privacy-minimized CPU/memory context: Local Apple Silicon workstation; no machine identifier or unrelated process inventory retained.
- Network availability/denial context: Deterministic development tests require no network; a later live promotion uses only the configured provider and optional Graphify endpoints.
- Seeds/repeats and uncertainty rule: Deterministic routing cases run on every suite pass. One expensive live run is development evidence only; any provider/environment ambiguity is `inconclusive`, not a promotion.

## Budgets

- Per candidate: One material routing mechanism, full deterministic suite, and at most one fresh live small run after the deterministic gates pass.
- Total candidates: Three focused candidates before reevaluating the evaluator or design.
- Total time/compute/tokens/money: Subscription-backed live calls only; no API-cost expansion. Stop before another medium/iOS run unless the small holdout promotes.
- Cost/latency/complexity ceilings: No second controller, classifier model, database, dependency, or case-specific branch. Candidate code should remain a small deterministic policy function plus receipt.

## Decisions

- Keep rule: The candidate deterministically routes only explicitly declared low-risk single-owner test-proof plans, preserves full routing everywhere else, and passes every preservation gate.
- Promotion rule: A fresh small holdout merges in no more than three successful calls with unchanged independent review; the untouched medium visual canary selects the full route; then the candidate may become default.
- Evaluator-hardening triggers: A route can be self-declared fast while using visual, prompt, optimization, delivery, multiple owners, excessive scope, or no test proof; call accounting omits retries/unknown usage; or the final reviewer is skipped.
- Stop conditions: Target reached and holdout passes; three candidates show no stable gain; any hard gate weakens; live evidence is inconclusive; or further work needs external authority.
- Human or external approval points: None during a configured autonomous local run. Deployment/publication remains separate explicit authority.

## Durable state

- Incumbent: Archived v18 `small-evaluation.json`—28/28, merged, 5 calls, 102,209 tokens, 1,038.218 seconds, one plan cycle, one review cycle.
- Candidate ledger: `evidence/factory-efficiency/candidates.jsonl` locally, with concise promoted results summarized in this document and the changelog.
- Trace/output directory: `evidence/factory-efficiency/` locally plus immutable target `.factory/runs/<id>` ledgers.
- Progress note: This document and `CHANGELOG.md`.
- Resume procedure: Verify the evaluator/data hashes above, inspect the latest candidate record, retain the last verified incumbent, and never tune on the fresh holdout after exposure.
