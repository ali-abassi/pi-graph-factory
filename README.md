# Pi Graph Factory

**Turn an approved software request into isolated implementation, fresh proof,
independent review, and a merge-authorizing receipt.**

Pi Graph Factory is a local, deterministic control plane for agentic software
work. Agents plan, design, code, and review. Controller code owns order,
approval, file scope, test execution, evidence identity, retry limits, and merge
authority.

```text
request or issue
      |
      v
planner -> blocking questions -> revised typed plan -> SHA-256 approval
                                                       |
                         +-----------------------------+
                         v
              1-10 isolated Git worktrees
                 |       |       |
                 +--- deterministic integration
                              |
                  tests + proportional proof
                              |
                      independent review
                         |            |
                      pass          repair
                         |            |
                  guarded merge   named owner
                                      |
                               fresh proof again
                         (five reviews maximum)
                         |
                  optional deploy + health
```

This repository is a public alpha for trusted local or Railway-hosted trials.
Read [VISION.md](VISION.md) for the intended product and
[docs/RAILWAY.md](docs/RAILWAY.md) for the off-laptop execution model.

## What works now

- Existing Git repositories and newly initialized repositories.
- Manual requests today; issue and webhook adapters can call the same `init`
  command.
- A configured read-only planner that produces a durable typed plan with
  blocking questions.
- Approval of the exact canonical plan SHA-256, never a conversational “yes.”
- One to ten active implementers running concurrently in isolated branches and
  worktrees.
- Pi, Claude Code, and Codex harnesses behind one normalized receipt contract.
- Conservative plan-time rejection of overlapping owner globs.
- Git-derived changed-file verification against each owner's approved scope.
- Mechanical execution of every approved task and integrated acceptance command.
- Deterministic lane integration with `git cherry-pick` and `git diff --check`.
- Plan-selected proof: tests for non-UI work, or screenshot/video/browser
  artifacts for UI and interaction work, all bound to the current commit and
  approved plan.
- Independent review that must cite the current evidence receipt hash.
- Review findings routed only to their named owners, with fresh checks and proof
  after every repair.
- Five review attempts maximum, then an explicit `human_required` terminal.
- One-writer run locking, durable `transition_failed` events, inspectable active
  processes, and checkpointed `resume` across interrupted lanes, repairs,
  capture, review, integration, and the post-merge state-save window.
- Per-role configurable or disabled process-group timeouts. Token and cost
  ceilings are optional and disabled in the subscription-friendly default.
- Safe fresh-repository ignore defaults and pre-integration rejection of
  caches, bytecode, dependency trees, and likely secret-bearing `.env` files.
- Fast-forward-only merge after target, plan, repository, tests, evidence, and
  final review all still match.
- An explicit optional delivery command with configured deploy, health, and
  rollback receipts.

## Quick start

Requirements: macOS or Linux, Python 3.10+, Git, and at least one configured
agent harness. Pi is the default:

```bash
git clone https://github.com/ali-abassi/pi-graph-factory.git
cd pi-graph-factory
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

pi  # authenticate once, then exit
```

Write a request, initialize a durable run, and ask the configured planner for
the smallest typed plan:

```bash
printf '%s\n' 'Add CSV export and prove it with tests.' > request.md

.venv/bin/python scripts/factory.py init \
  --repo /path/to/project \
  --config factory.yaml \
  --request-file request.md

.venv/bin/python scripts/factory.py plan \
  --run /path/to/project/.factory/runs/RUN_ID \
  --generate
```

If the result contains blocking questions, answer them and generate a revised
plan:

```bash
.venv/bin/python scripts/factory.py answer \
  --run /path/to/project/.factory/runs/RUN_ID \
  --question QUESTION_ID \
  --answer 'The requested behavior'

.venv/bin/python scripts/factory.py plan \
  --run /path/to/project/.factory/runs/RUN_ID \
  --generate
```

Inspect the emitted `plans/plan-N.json`. Approval is deliberately separate:

```bash
.venv/bin/python scripts/factory.py approve \
  --run /path/to/project/.factory/runs/RUN_ID \
  --sha256 PLAN_SHA256

.venv/bin/python scripts/factory.py run \
  --run /path/to/project/.factory/runs/RUN_ID

.venv/bin/python scripts/factory.py inspect \
  --run /path/to/project/.factory/runs/RUN_ID
```

If the controller or its agent process is interrupted, inspect first and then
continue validated checkpoints:

```bash
.venv/bin/python scripts/factory.py resume \
  --run /path/to/project/.factory/runs/RUN_ID

# Only after inspecting a still-live factory-owned process:
.venv/bin/python scripts/factory.py resume \
  --run /path/to/project/.factory/runs/RUN_ID \
  --terminate-active
```

`status` returns the full machine-readable state. `inspect` is the concise
operator view: current operation, active agents, lane/worktree status, last
error, and paths to every plan, context, receipt, event, and evidence record.

Use `plan --file plan.json` when another trusted system produces the plan. Use
`init --new-repo` when the target path does not exist.

Every command emits one JSON object. The run directory contains frozen config,
plan revisions, normalized agent receipts, contexts, isolated worktrees,
append-only events, evidence manifests, state, and—only after every gate
passes—`receipt.json`.

## The plan contract

The planner and controller share a small contract:

```json
{
  "version": 1,
  "summary": "Add CSV export",
  "proof": {
    "mode": "tests",
    "reason": "This backend-only change has no user interface behavior."
  },
  "success_criteria": [
    {"id": "SC-1", "description": "A user can export the current dataset as CSV."}
  ],
  "tasks": [
    {
      "id": "export-api",
      "owner": "product",
      "files": ["src/export/**", "tests/export/**"],
      "acceptance": ["pytest tests/export -q"]
    }
  ],
  "acceptance": ["pytest -q"],
  "risks": ["Large exports may require streaming"],
  "open_questions": []
}
```

File patterns must stay inside the repository. Different owners cannot receive
patterns the controller considers overlapping. After implementation, Git's
actual staged paths—not the model's claim—must match the approved owner scope.
The controller then runs each task's approved commands before committing its
lane, and reruns top-level acceptance on the integrated commit every review
cycle.

With the default `evidence.policy: plan`, version 1 plans must choose
`proof.mode: tests|visual` and explain why. The planner is instructed to use
visual proof for UI, interaction, responsive, or explicitly demonstrated
features—not for documentation, refactors, backend-only work, or tiny non-UI
changes.

Version 1 plans make approved outcomes explicit. The reviewer must return one
pass/fail entry with concrete inspected evidence for every success criterion in
the original order; missing, duplicate, unknown, or failed-but-unrouted criteria
cannot authorize merge. Each issue must name exact `target_files` inside its
routed owner's approved scope, preventing a valid-looking issue from dispatching
the wrong lane. Unversioned plan files remain accepted only for legacy
compatibility. Generated plans always use version 1.

Plan commands are executable code. Approval therefore means reviewing file
scope and commands as well as prose.

## Configure agents

Edit [`factory.yaml`](factory.yaml) to choose each role's harness, model,
thinking level, instructions, skills, and tools. The example uses Pi for product
work and independent review, and Claude Code for design work.

Supported harness identifiers are:

- `pi`
- `claude-code`
- `codex`

Only owners present in the approved plan launch. All active initial lanes run
concurrently; integration and state transitions remain serialized. Review
repairs run only for owners named in typed findings.

Pi usage is read from its settled assistant event. Claude Code and Codex usage
remains `null` unless their local harness output exposes it. The factory does
not invent token or cost numbers.

## Limits and usage

Timeouts may be configured globally or per role. Use `null` to disable a
timeout. Optional dispatch ceilings are also `null` by default because Codex
and Claude Code subscription sessions are not API-metered factory budgets:

```yaml
planner:
  timeout_seconds: 7200
implementers:
  - id: product
    timeout_seconds: 14400
limits:
  agent_timeout_seconds: 14400
  command_timeout_seconds: 3600
  termination_grace_seconds: 30
  max_total_tokens: null
  max_total_cost_usd: null
  require_usage: false
```

An expired agent or approved shell command is terminated as a process group
after the configured grace period. Set either timeout to `null` when the
environment should allow unbounded runtime. Every normalized call receipt is
durable, and aggregate usage appears in state and the final receipt.
When a ceiling is explicitly configured, the controller refuses the next
planner, reviewer, or repair dispatch after it is reached. Initial implementers
start as one approved parallel batch, so already-running lanes can collectively
cross a ceiling before subsequent work stops. Set `require_usage: true` to
refuse further dispatch after a harness reports unknown usage; provider-side
budgets remain the only hard external spend cap.

## Evidence and review

The target project owns meaningful capture automation. Under the default
`policy: plan`, test-only plans skip capture commands and do not require media.
Visual plans run the configured screenshot, video, and browser capture.
`policy: always` forces visual proof; `policy: never` forces tests only.
Configure capture and test paths under `evidence` in `factory.yaml`.
Proof paths must survive lane commits and integration, so keep them in a
project-owned tracked directory such as `evidence/factory/`, never under the
controller's ignored `.factory/` run-state directory.

`capture_commands` run on the clean integrated worktree before evidence tests
and again after every repair. They may change only declared screenshots, video,
and `artifacts`; the controller commits those exact proof files, rejects stray
writes, and binds review to the resulting commit. This lets frontend capture
exercise backend or product work from other lanes without weakening lane
isolation.

Task, plan, and evidence-test acceptance commands are read-only predicates.
They cannot repeat configured capture commands or mutate repository files after
scope/proof validation. Reviewers are also mechanically prevented from changing
the integration tree they judge.

For every review cycle the controller:

1. runs approved integrated acceptance and configured evidence tests;
2. for visual plans, captures and rejects missing, empty, absolute, or
   repository-escaping proof paths;
3. hashes each visual proof file;
4. binds the manifest to the integration commit and approved plan;
5. asks the independent reviewer for a typed `pass` or `repair` verdict; and
6. requires the reviewer to cite that exact manifest hash.

Any repair changes the commit, invalidates the old proof, and triggers capture
and review again. File existence and provenance are mechanical. Semantic visual
quality still depends on the configured browser/native capture and independent
reviewer.

If a declared capture command fails without writing outside its declared proof
paths, the controller restores the clean integration commit, hashes a failed
capture receipt, and asks the independent reviewer to route a repair inside the
same five-cycle budget. Partial proof can never authorize merge.

Malformed reviewer JSON gets one controller-guided validation retry against the
same commit, evidence, and review cycle. Both attempts are durable; a second
invalid response fails closed rather than consuming repair cycles or looping.
Malformed planner JSON is normalized into a usage-bearing invalid receipt and
gets the same two-attempt bound; a single JSON code fence is accepted, while
arbitrary surrounding prose is not. A repair that completed its code change but
returned the wrong `addressed` ids gets one receipt-only correction with read
tools and an exact staged-diff fingerprint. Any correction-time mutation or
second invalid receipt fails closed.

## Merge policy

`merge.apply: false` is the safe default. A successful run ends at
`merge_ready` with a merge-authorizing receipt but does not change the target
branch. Set `apply: true` only for a trusted local environment that should
fast-forward automatically.

Merge is refused unless:

1. the current plan is still the exact approved plan;
2. the frozen factory config and repository identity still match;
3. every active lane stayed inside approved scope and passed approved checks;
4. the independent final review passes with no open issues;
5. tests and evidence belong to the current integration commit and plan;
6. the target branch has not moved and its checkout is clean; and
7. `git diff --check` passes.

## Delivery policy

Delivery is disabled by default. To enable it, automatic merge must also be
enabled and the frozen contract must provide non-empty deploy and health
commands:

```yaml
merge:
  target: main
  apply: true
delivery:
  enabled: true
  deploy_commands: ["railway up --detach"]
  health_commands: ["curl --fail --retry 12 https://example.com/health"]
  rollback_commands: ["./scripts/rollback-production"]
```

A successful run stops at `delivery_ready`; production mutation is a separate,
explicit action:

```bash
.venv/bin/python scripts/factory.py deliver --run /path/to/RUN_ID
```

The controller records deploy and health output and attempts the configured
rollback after failure. Commands must be designed to be idempotent: an abrupt
machine death during an arbitrary external command cannot be made exactly-once
by local state alone.

## Pi Graph contract

The canonical repository-mutation path today is `scripts/factory.py`. The
factory config also compiles into an inspectable Pi Graph Core workflow showing
the same bounded topology: parallel roles, evidence, per-cycle pass/repair
branches, five guarded merge exits, and final human escalation.

Generated YAML is intentionally not committed:

```bash
.venv/bin/python scripts/compile_factory.py factory.yaml \
  --out /tmp/factory.steps.yaml

python3 -m pip install \
  'git+https://github.com/ali-abassi/pi-graph-core.git@v0.1.0'
piw validate /tmp/factory.steps.yaml --strict
piw graph /tmp/factory.steps.yaml
```

The compiled graph is currently a policy/template surface, not a second
authoritative lifecycle state store. Keeping one canonical controller avoids
the two-engine drift this repository previously had.

## Verification

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m ruff check scripts tests
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile scripts/*.py tests/*.py
```

The deterministic suite currently covers 67 cases, including:

- simple single-owner first-pass work;
- a two-owner feature with directed design repair;
- a three-owner application with two directed repairs;
- clarification and generated planning;
- wrong-plan approval, scope escape, overlapping ownership, forged receipts,
  stale evidence citations, and failed approved commands;
- real concurrent lanes, second-writer exclusion, durable caught failures;
- interrupted-agent termination, committed-lane and committed-repair recovery,
  and recovery of a reviewed fast-forward applied before state persistence;
- agent process-group timeout, token-limit refusal, safe new-repository
  bootstrap, and generated/secret-bearing artifact refusal;
- versioned success-criteria requirements, exact review coverage, and refusal
  of omitted or partial outcome accounting;
- post-integration capture refresh, capture-command failure, and declared-only
  proof writes;
- refusal of duplicate capture/acceptance commands, acceptance-time repository
  mutation, ignored proof artifacts, and reviewer writes;
- failed-capture cleanup, forced repair routing, recapture, and refusal of a
  reviewer pass against invalid proof;
- one corrected reviewer-protocol retry and bounded refusal after two malformed
  reviewer responses;
- planner JSON normalization and one bounded typed-plan correction;
- exact review-issue target files bound to the routed owner's approved scope;
- one read-only repair-receipt correction and refusal of correction-time writes;
- fresh proof after repair, successful merge, target/config drift, and bounded
  human escalation.

CI runs the suite on Ubuntu and macOS with Python 3.10 and 3.14, compiles the
24-node policy graph, and validates it with the public Pi Graph Core release.
The measured hill-climb and candidate ledger are in
[`docs/IMPROVEMENT.md`](docs/IMPROVEMENT.md) and
[`docs/improvement-ledger.jsonl`](docs/improvement-ledger.jsonl).

## Deliberate boundaries

- Agent and approved test commands execute with the invoking account's
  permissions. Local mode intentionally supports broad trusted permissions; use
  the Railway execution mode to move builds off the laptop, not as a claim of a
  hostile-code sandbox.
- Validated checkpoints recover interrupted lane work, owner-scoped partial
  repairs, declared capture artifacts, committed repairs, and an already-applied
  reviewed fast-forward. Ambiguous changes, cross-owner conflicts, and unknown
  processes still stop for an operator.
- `--terminate-active` kills only a recorded process group whose live command
  still matches the factory role. Child-created background daemons outside that
  process group remain an execution-environment concern.
- GitHub issue/webhook ingestion and a hosted clarification UI are adapters, not
  bundled services.
- Cross-lane cherry-pick conflicts stop for a human; the factory does not let a
  model invent conflict resolution across owners.
- Screenshot semantics, video duration, accessibility, console/network quality,
  deployment, rollback, and production health must be expressed by the target
  project's approved commands and reviewer policy. External delivery commands
  are not transactionally exactly-once across machine death.
- Provider behavior and credentials are external dependencies. Never place
  secrets in requests, plans, prompts, command arguments, or committed evidence.

These are product boundaries, not footnotes. Read [`SECURITY.md`](SECURITY.md)
before allowing agents to modify a sensitive repository.

## Project

- [Changelog](CHANGELOG.md)
- [Vision](VISION.md)
- [Railway Cloud Agents](docs/RAILWAY.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [MIT license](LICENSE)
