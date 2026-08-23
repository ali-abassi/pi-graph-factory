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
                     tests + screenshot/video hashes
                              |
                      independent review
                         |            |
                      pass          repair
                         |            |
                  guarded merge   named owner
                                      |
                               fresh proof again
                         (five reviews maximum)
```

This repository is an alpha. It proves the local factory contract; it is not a
hosted sandbox or an unattended deployment service.

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
- Screenshot, video, browser, and test receipts bound to the current commit and
  approved plan.
- Independent review that must cite the current evidence receipt hash.
- Review findings routed only to their named owners, with fresh checks and proof
  after every repair.
- Five review attempts maximum, then an explicit `human_required` terminal.
- One-writer run locking and durable `transition_failed` events.
- Configured process-group timeouts plus token and cost dispatch ceilings.
- Safe fresh-repository ignore defaults and pre-integration rejection of
  caches, bytecode, dependency trees, and likely secret-bearing `.env` files.
- Fast-forward-only merge after target, plan, repository, tests, evidence, and
  final review all still match.

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

.venv/bin/python scripts/factory.py status \
  --run /path/to/project/.factory/runs/RUN_ID
```

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

Version 1 plans make approved outcomes explicit. The reviewer must return one
pass/fail entry with concrete inspected evidence for every success criterion in
the original order; missing, duplicate, unknown, or failed-but-unrouted criteria
cannot authorize merge. Unversioned plan files remain accepted only for legacy
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

`limits` in `factory.yaml` bounds each agent call and later dispatches:

```yaml
limits:
  agent_timeout_seconds: 1800
  max_total_tokens: 500000
  max_total_cost_usd: 10
  require_usage: false
```

An expired agent is terminated as a process group. Every normalized call
receipt is durable, and aggregate usage appears in state and the final receipt.
The controller refuses the next planner, reviewer, or repair dispatch once a
configured token or cost ceiling is reached. Initial implementers start as one
approved parallel batch, so already-running lanes can collectively cross a
ceiling before the controller stops subsequent work. Set `require_usage: true`
to refuse further dispatch after a harness returns unknown token or cost usage;
provider-side budgets remain the only hard external spend cap.

## Evidence and review

The target project owns meaningful capture automation. Configure screenshot,
video, browser-receipt, and test paths under `evidence` in `factory.yaml`.
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

1. runs approved integrated acceptance and configured evidence commands;
2. rejects missing, empty, absolute, or repository-escaping proof paths;
3. hashes each proof file;
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

The deterministic suite currently covers 45 cases, including:

- simple single-owner first-pass work;
- a two-owner feature with directed design repair;
- a three-owner application with two directed repairs;
- clarification and generated planning;
- wrong-plan approval, scope escape, overlapping ownership, forged receipts,
  stale evidence citations, and failed approved commands;
- real concurrent lanes, second-writer exclusion, durable caught failures;
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
- fresh proof after repair, successful merge, target/config drift, and bounded
  human escalation.

CI runs the suite on Ubuntu and macOS with Python 3.10 and 3.14, compiles the
24-node policy graph, and validates it with the public Pi Graph Core release.
The measured hill-climb and candidate ledger are in
[`docs/IMPROVEMENT.md`](docs/IMPROVEMENT.md) and
[`docs/improvement-ledger.jsonl`](docs/improvement-ledger.jsonl).

## Deliberate boundaries

- Agent and approved test commands execute with the invoking user's local
  permissions. This is not an untrusted-code sandbox.
- Caught controller failures are durable and fail `status` closed. Automatic
  recovery of dirty partial agent work, cancellation, and remote worker recovery
  are not implemented yet; inspect the run and worktrees before retrying.
- A killed controller releases its OS lock, but a partially executing child
  harness may need operator cleanup.
- GitHub issue/webhook ingestion and a hosted clarification UI are adapters, not
  bundled services.
- Cross-lane cherry-pick conflicts stop for a human; the factory does not let a
  model invent conflict resolution across owners.
- Screenshot semantics, video duration, accessibility, console/network quality,
  deployment, rollback, and production health must be expressed by the target
  project's approved commands and reviewer policy.
- Provider behavior and credentials are external dependencies. Never place
  secrets in requests, plans, prompts, command arguments, or committed evidence.

These are product boundaries, not footnotes. Read [`SECURITY.md`](SECURITY.md)
before allowing agents to modify a sensitive repository.

## Project

- [Changelog](CHANGELOG.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [MIT license](LICENSE)
