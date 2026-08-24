# Pi Graph Factory

**Turn a software request into an independently planned, implemented, proven,
and reviewed change without making a person operate the workflow.**

Pi Graph Factory is a local, deterministic control plane for agentic software
work. Agents plan, design, code, and review. Controller code owns order,
approval, file scope, test execution, evidence identity, retry limits, and merge
authority.

```text
request or issue
      |
      v
interactive grill (+ optional domain docs) | autonomous self-grill | direct
      |
      v
Graphify + VISION.md + FEATURE_MAP.md + TASTE.md
      |
      v
planner <-> independent plan judge (8.5/10, three cycles maximum)
      |
      +-> uncertainty returns as assumption-revision feedback
      |
      v
judge authorizes the exact typed-plan SHA-256
      |
      v
       1-10 specialist implementers in isolated Git worktrees
       product | UI design | visual assets | copy | prompt | optimization | configured
             |          |               |        |        |              |
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
                   (continues until criteria pass)
                         |
                  optional deploy + health
```

This repository is a public alpha for trusted local or Railway-hosted trials.
Read [VISION.md](VISION.md) for the intended product and
[docs/RAILWAY.md](docs/RAILWAY.md) for the off-laptop execution model.

## What works now

- Existing Git repositories and newly initialized repositories.
- Direct, interactive, and autonomous intake with durable, hashed artifacts.
  Issue and webhook adapters can call the same `init` command.
- Interactive intake accepts a ready `goal-brief.md`; autonomous intake accepts
  and validates a `self-grilled-brief.md` plus its structured decision ledger.
- Automatic Graphify setup and commit-aware refresh for code repositories,
  with DeepSeek V4 Flash enrichment of repository docs and community labels;
  code-free new projects defer indexing until implementation creates code.
- Durable `VISION.md`, `FEATURE_MAP.md`, and project-specific `TASTE.md` memory,
  with up to 75,000 characters of each supplied to planning. Generated plans
  must create any missing file and the memory receipt names truncation.
- A graph-first, read-only planner that records repository research and
  defensible assumptions before producing a durable typed plan.
- An independent rubric judge whose score is recomputed by the controller.
  Plans below 8.5/10 return to the planner for at most three quality cycles.
- Autonomous assumption revision when a planner proposes a blocking question;
  the judge still applies the same quality threshold to the revised plan.
- Judge authorization of the exact canonical generated-plan SHA-256 after every
  critical rubric dimension clears the configured bar. Human approval remains
  an opt-in mode and is always required for externally supplied plan files.
- A single `start` command that initializes, plans, authorizes, implements,
  proves, reviews, repairs, and reaches the configured merge outcome without a
  human planning checkpoint. Terminal failures remain explicit and inspectable.
- One to ten active implementers running concurrently in isolated branches and
  worktrees.
- Configured specialist ownership: product, UI design, generated visual assets,
  copywriting, prompt engineering, and measured optimization by default, with
  only specialists named in the approved plan dispatched. The default visual-
  asset lane uses Codex with built-in OpenAI image generation and never shares
  UI-code ownership.
- Pi, Claude Code, and Codex harnesses behind one normalized receipt contract.
- [Ponytail](https://github.com/DietrichGebert/ponytail)-derived minimal-code
  discipline during implementation and an explicit over-engineering lens during review.
- Public-seam TDD for changed executable behavior and reproduce-diagnose-regress
  discipline for bugs, without imposing test ceremony on docs or metadata.
- One clear-prose skill shared by every role: preserve facts and technical terms,
  name evidence gaps, cut generic AI filler, and never rewrite typed contracts.
- The `evil-genius-copywriter` discipline for product, UX, website, repository,
  lifecycle, and promotional copy: 80/20 reader diagnosis, one central tension,
  a distinctive mechanism, truthful behavioral leverage, exact constraints,
  and honest performance boundaries.
- Production prompt engineering with a controller-required runtime, trust,
  host-enforcement, schema, abstention, and six-case evaluation contract.
- AutoAgent-shaped hill climbing for genuine optimization tasks: controller-run
  baseline/scoring/gates, one isolated candidate per dispatch, protected-file
  fingerprints, candidate/plateau/time budgets, and one promotion run.
- New-product and major-redesign plans require inspected public visual research,
  competing directions, project taste, explicit screens/states/assets, an
  originality boundary, an observable quality bar, and a real matching-surface
  verification driver. Incremental UI work follows the existing system without
  unnecessary prototype ceremony.
- Conservative plan-time rejection of overlapping owner globs.
- Git-derived changed-file verification against each owner's approved scope.
- Mechanical execution of every approved task and integrated acceptance command.
- Deterministic lane integration with `git cherry-pick` and `git diff --check`.
- Plan-selected proof: tests for non-UI work, or screenshot/video/browser
  artifacts for UI and interaction work, all bound to the current commit and
  approved plan.
- Independent review that must cite the current evidence receipt hash and apply
  proportional adversarial, taste, project-verification, and minimality lenses.
- Review findings routed only to their named owners, with fresh checks and proof
  after every repair.
- Unlimited review/repair cycles by default. Every blocking issue must cite a
  failed approved success criterion; optional finite caps end in an explicit
  `human_required` terminal and can be deliberately reopened for unlimited review.
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

Requirements: macOS or Linux, Python 3.10+, Git, `uv` for the default pinned
Graphify auto-install, and at least one configured agent harness. Pi is the
default:

```bash
git clone https://github.com/ali-abassi/pi-graph-factory.git
cd pi-graph-factory
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install uv

pi  # authenticate once, then exit

# The default semantic-enrichment model must also report ready:
pi auth check \
  --model baseten/deepseek-ai/DeepSeek-V4-Flash-0731 \
  --no-refresh
```

Graphify is deliberately not part of the small base requirements. On the first
code-repository planning run, the controller uses `uv` to run the pinned
`graphifyy==0.9.48` package. You may instead install that package yourself or
set `PI_GRAPH_FACTORY_GRAPHIFY` to an explicit trusted Graphify command.

The default config asks Graphify to enrich repository docs and community labels
with `baseten/deepseek-ai/DeepSeek-V4-Flash-0731`. The controller obtains that
credential from Pi in memory, passes it only to the Graphify child process, and
never writes it to a receipt or command argument. This Baseten call is API-metered;
it is separate from Codex or Claude Code subscriptions. If it is not configured,
the public default records the failure and falls back to the deterministic AST
map. Set `intelligence.enrichment.required: true` to fail closed instead.

Write a request and start the factory. With the default `approval.mode: judge`,
the controller takes over after intake:

```bash
printf '%s\n' 'Add CSV export and prove it with tests.' > request.md

.venv/bin/python scripts/factory.py start \
  --repo /path/to/project \
  --config factory.yaml \
  --request-file request.md
```

Automatic merge remains separately configurable. The public default reaches a
merge-authorizing `merge_ready` receipt; set `merge.apply: true` in the run
contract when a passing review should fast-forward the target branch.

For a broad new idea, choose intake before initialization:

- `interactive` preserves a human-led `goal-brief.md` produced by `/grill-me`
  (phone), `goal-grill` (text), or `/grill-with-docs` when the project also needs
  durable domain context and selective ADRs.
- `auto` validates a `/grill-yourself` brief and decision ledger, including
  coverage, confidence, reversibility, and the absence of unresolved human-only
  decisions.
- `direct` remains the default for an already-specific issue or request.

See [Intake modes](docs/INTAKE.md) for the exact commands and contracts. All
three paths converge on the same planner and independent plan-quality gate.

The default path does not stop for planning questions. If a candidate plan
contains one, the controller sends it back to the planner, which must select the
safest evidence-backed reversible assumption, record it, and face the independent
judge again. Context belongs in the request, `VISION.md`, `FEATURE_MAP.md`, or an
interactive/auto intake brief before `start`; after that command, the process owns
the plan-to-merge lifecycle.

The `answer` command exists only for contracts that explicitly select human
governance:

```bash
.venv/bin/python scripts/factory.py answer \
  --run /path/to/project/.factory/runs/RUN_ID \
  --question QUESTION_ID \
  --answer 'The requested behavior'
```

For step-by-step inspection, initialize first and use `advance`. It performs
whatever autonomous transition is currently valid: generated planning from
`intake`, or execution from an authorized plan:

```bash
.venv/bin/python scripts/factory.py init \
  --repo /path/to/project \
  --config factory.yaml \
  --request-file request.md

.venv/bin/python scripts/factory.py advance \
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

To continue a run that stopped at a configured review cap without rebuilding
its implementation, reopen only that exhausted review terminal:

```bash
.venv/bin/python scripts/factory.py resume \
  --run /path/to/project/.factory/runs/RUN_ID \
  --unlimited-reviews
```

`status` returns the full machine-readable state. `inspect` is the concise
operator view: current operation, active agents, last meaningful activity,
lane/worktree status, aggregate usage, blockers, and paths to every plan,
attempt-specific context, raw log directory, receipt, event, and evidence record.

Use `plan --file plan.json` only when another trusted system already produced
and reviewed the plan; this path intentionally bypasses generated-plan research
and the LLM plan judge, so it always requires exact human SHA-256 approval with
`approve` before `run`. Set `approval.mode: human` when generated plans should
also stop for that ceremony. Use `start --new-repo` when the target path does
not exist.

Every command emits one JSON object. The run directory contains frozen config,
preserved intake, plan revisions, normalized agent receipts, immutable per-attempt
contexts, private raw adapter/harness logs, copied native Claude transcripts,
isolated worktrees, append-only events, evidence manifests, state, and—only after
every gate passes—`receipt.json`.

## Repository intelligence and project memory

Before generated planning, the controller inspects the target commit:

- If supported source code exists, it creates or refreshes
  `graphify-out/graph.json`. A small local metadata receipt prevents needless
  extraction until the commit changes.
- Code structure comes from deterministic AST extraction. When enabled,
  Graphify's LLM pass enriches docs, papers, images, and community labels. The
  planner then reasons over that combined map and verifies important claims in
  source; the project is not pretending an LLM rewrote the AST.
- If the repository has no code yet, Graphify reports `deferred`; the planner
  starts from the request and project memory. After successful implementation,
  the controller builds the first graph before merge authorization.
- If `VISION.md`, `FEATURE_MAP.md`, or `TASTE.md` is absent from an existing
  repository, the generated plan must assign creation of that file to an
  implementation owner. `TASTE.md` is project-scoped; the factory does not copy
  an unrelated global or terminal-specific palette into a new app.
- Each document contributes at most 75,000 characters to planning context. The
  memory receipt explicitly lists any document that exceeded that boundary.
- Graphify output is added to the repository's local Git exclude and is never a
  product artifact. The durable run keeps compact intelligence and project-
  memory receipts under `.factory/runs/RUN_ID/intelligence/`.

The graph is an index for finding relevant code, not proof. Planner and
implementer instructions require focused graph queries followed by verification
against current source files. This avoids broad context dumps without trusting
a stale or lossy map.

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
  "research": [
    {
      "question": "Where does export behavior belong?",
      "finding": "The existing export service owns serialization.",
      "evidence": ["Graphify: ExportService", "src/export/service.py"]
    }
  ],
  "assumptions": ["Preserve the existing UTF-8 download convention."],
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
If a lane creates new out-of-scope scaffolding in its disposable worktree, the
controller discards those exact untracked paths, records a scope-correction
receipt, and validates the remaining Git change and reported file list again.
An out-of-scope edit to any tracked file still fails closed. Generated caches,
secret-bearing files, acceptance-command mutations, and integration drift are
never corrected this way.
Agents should not commit lane work. If one creates only linear descendant
commits on its assigned disposable branch, the controller records their hashes,
soft-resets to the pre-dispatch baseline, and validates the complete delta before
creating the authoritative lane commit. A detached/switched branch, amended or
replaced baseline, or merge commit fails closed.
The controller then runs each task's approved commands before committing its
lane, and reruns top-level acceptance on the integrated commit every review
cycle.

With the default `evidence.policy: plan`, version 1 plans must choose
`proof.mode: tests|visual` and explain why. The planner is instructed to use
visual proof for UI, interaction, responsive, or explicitly demonstrated
features—not for documentation, refactors, backend-only work, or tiny non-UI
changes.

Generated version 1 plans also require non-empty repository research and an
explicit assumptions array. The controller validates their shape; the
independent plan reviewer scores grounding, coverage, feasibility, minimality,
and alignment using anchored half-point ratings. Grounding and feasibility are
critical: either may fail below the numeric scale. The controller recomputes
the weighted total and accepts `pass` only at the configured threshold (8.5 by
default). A failed judgment and its rubric-linked improvements return to the
planner. Three unsuccessful quality cycles fail closed. By default, a passing
judgment authorizes the exact generated-plan hash; `approval.mode: human`
restores a separate operator approval step. If the planner proposes a blocking
question under judge authority, the controller treats it as revision feedback:
the planner must choose and record the safest evidence-backed reversible
assumption before the plan can pass.

Generated visual plans carry a controller-validated `visual_contract`. For a
new product or major redesign it requires at least three unique inspected
references, two distinct directions, three design principles, and three
observable quality-bar outcomes. It also declares the audience, selected
direction, screens and adverse states, every asset's source/owner/path,
originality boundary, real verification surface and driver, proof artifacts,
and success-criterion coverage. Generated raster files must belong to the
`visual-assets` owner; UI code remains with `design`. The reviewer then checks
the built experience against this frozen contract instead of deciding whether
it merely compiles.

Version 1 plans make approved outcomes explicit. The implementation reviewer must return one
pass/fail entry with concrete inspected evidence for every success criterion in
the original order; missing, duplicate, unknown, or failed-but-unrouted criteria
cannot authorize merge. Each issue must name exact `target_files` inside its
routed owner's approved scope, preventing a valid-looking issue from dispatching
the wrong lane. Unversioned plan files remain accepted only for legacy
compatibility. Generated plans always use version 1.

Plan commands are executable code. Authorization therefore covers file scope
and commands as well as prose; select human mode when those commands require an
operator's direct review.

## Configure agents

Edit [`factory.yaml`](factory.yaml) to choose each role's harness, model,
thinking level, instructions, skills, and tools. The example uses Pi for product,
copywriting, prompt engineering, optimization, planning, and independent review;
Claude Code for UI design; and Codex Luna xhigh for generated visual assets.

Configured skills are native `--skill` inputs for Pi. For Claude Code and Codex,
the adapter reads the same trusted local `SKILL.md` files into the role prompt,
so a configured skill is not silently ignored when a lane changes harness. The
default product and design lanes include `skills/tdd`,
`skills/diagnosing-bugs`, and `skills/ponytail`; product, design, copywriter, and
reviewer receive `skills/evil-genius-copywriter` as a conditional lens for material
reader-facing messaging. Product/prompt owners receive
`skills/prompt-engineering`; the optimization owner receives the bounded
`skills/improvement` contract plus `skills/autoagent` patterns. Review receives
the corresponding lenses plus `skills/adversarial-review`, `skills/taste`,
`skills/project-verification`, and `skills/ponytail-review`. Planning receives
conditional decision, deep-thinking, visual-research, taste, and verification
skills. The visual-assets lane receives the image-generation contract. Every role receives
`skills/clear-prose` for its human-readable fields. These are conditional
disciplines inside existing roles, not extra controller lifecycles.
The placement decisions for the broader
engineering skill set are documented in
[Engineering skill decisions](docs/ENGINEERING_SKILLS.md); the ten-source prose
review is in [Prose skill decisions](docs/PROSE_SKILLS.md), and the bounded
search contract is in [Prompt and optimization](docs/PROMPT_OPTIMIZATION.md).
The source-level pstack review and adopt/bank/reject decisions are in
[pstack source review](docs/PSTACK_SKILLS.md).

Supported harness identifiers are:

- `pi`
- `claude-code`
- `codex`

With evidence policy `plan`, a tests-only plan does not run configured capture
commands or require configured screenshot, video, or browser-artifact paths.
Never create placeholder media for non-visual work. Visual plans activate the
configured capture command and declared artifacts after integration.

Only owners present in the approved plan launch. All active initial lanes run
concurrently; integration and state transitions remain serialized. Review
repairs run only for owners named in typed findings.

Pi usage is read from its settled assistant event. Claude Code usage is derived
from unique message ids in its preserved native transcript, including cache
creation/read tokens without double-counting repeated JSONL records. Codex usage
remains `null` unless its local harness output exposes it. The factory does not
invent token or cost numbers.

## Limits and usage

Timeouts may be configured globally or per role. Use `null` to disable a
timeout. Optional dispatch ceilings are also `null` by default because Codex
and Claude Code subscription sessions are not API-metered factory budgets:

```yaml
planner:
  timeout_seconds: 7200
plan_review:
  min_score: 8.5
  max_cycles: 3
  timeout_seconds: 7200
approval:
  mode: judge  # use human for a separate operator checkpoint
intelligence:
  provider: graphify
  required: true
  auto_install: true
  enrichment:
    enabled: true
    required: false
    backend: deepseek
    model: deepseek-ai/DeepSeek-V4-Flash-0731
    mode: deep
    base_url: https://inference.baseten.co/v1
    pi_auth_model: baseten/deepseek-ai/DeepSeek-V4-Flash-0731
implementers:
  - id: product
    timeout_seconds: 14400
  - id: design
    timeout_seconds: 14400
    fallbacks:
      - harness: pi
        model: openai-codex/gpt-5.6-luna
        thinking: xhigh
  - id: copy
    timeout_seconds: 14400
review:
  max_cycles: null       # unlimited; use a positive integer for a finite cap
  projection_cycles: 5   # finite window shown by the inspectable Pi Graph DAG
limits:
  agent_timeout_seconds: 14400
  command_timeout_seconds: 3600
  termination_grace_seconds: 30
  max_agent_attempts: 3
  agent_retry_backoff_seconds: 5
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
capture receipt, and asks the independent reviewer to route a repair through
the same review loop. Partial proof can never authorize merge.

Malformed reviewer JSON gets one controller-guided validation retry against the
same commit, evidence, and review cycle. Both attempts are durable; a second
invalid response fails closed rather than consuming repair cycles or looping.
Malformed planner JSON is normalized into a usage-bearing invalid receipt and
gets the same two-attempt bound; a single JSON code fence is accepted, while
arbitrary surrounding prose is not. An initial implementer that completed its
work but returned a malformed receipt gets one receipt-only correction with read
tools and an exact staged-diff fingerprint. A repair that returned the wrong
`addressed` ids receives the same treatment. Any correction-time mutation or
second invalid receipt fails closed. A provably linear agent-created lane commit
can be normalized and corrected on resume; rewritten baselines, merge history,
blocked receipts, and out-of-scope changes remain terminal.

Provider transport failures are a separate boundary. HTTP 408, 429, 5xx/529
overload responses and recognized temporary connection failures receive a
bounded retry of the same agent invocation. `limits.max_agent_attempts` includes
the first call; `limits.agent_retry_backoff_seconds` controls exponential
backoff. Every failed provider attempt is preserved as a redacted receipt, while
its private local adapter/harness streams remain in the attempt log directory;
the successful agent receipt records its attempt count. Authentication, billing,
permission, timeout, malformed-output, and semantic failures are not retried by
this mechanism. If every transient attempt on the preferred provider fails, the
controller may advance through at most two explicitly configured `fallbacks`.
Fallbacks inherit the same instructions, skills, tools, timeout, context,
worktree, scope checks, and acceptance contract; they may override only harness,
model, thinking, and timeout. The final receipt names both the requested and
selected providers. No fallback occurs for a permanent, protocol, or semantic
failure.

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
a finite window of the same topology: repository intelligence, planning and its
independent quality gate, parallel roles, evidence, per-cycle pass/repair
branches, guarded merge exits, and explicit continuation by the canonical
controller when reviews are unlimited.

Generated YAML is intentionally not committed:

```bash
.venv/bin/python scripts/compile_factory.py factory.yaml \
  --out /tmp/factory.steps.yaml

python3 -m pip install \
  'git+https://github.com/ali-abassi/agent-workflows.git@v0.2.0'
piw validate /tmp/factory.steps.yaml --strict
piw graph /tmp/factory.steps.yaml
```

The compiled graph is currently a policy/template surface, not a second
authoritative lifecycle state store. Its plan-review node blocks a low score;
the canonical controller owns the feedback-bearing three-cycle revision loop.
Keeping one lifecycle owner avoids two-engine drift.

## Verification

```bash
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m ruff check scripts tests
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m py_compile scripts/*.py tests/*.py
```

The deterministic suite currently covers 107 cases, including:

- simple single-owner first-pass work;
- a two-owner feature with directed design repair;
- a three-owner application with two directed repairs;
- one-command autonomous execution, judge-bound plan authorization, automatic
  assumption revision without a human pause, optional human approval, and
  generated planning;
- Graphify deferral, first indexing, commit-aware reuse, and stale refresh;
- DeepSeek semantic-enrichment dispatch, credential non-persistence, and explicit
  AST fallback when optional enrichment is unavailable;
- missing project-memory assignment and a two-cycle under-8.5 plan revision;
- refusal of a plan judge's forged weighted score or a weak critical dimension
  hidden behind a passing average;
- wrong-plan approval, scope escape, overlapping ownership, forged receipts,
  stale evidence citations, and failed approved commands;
- real concurrent lanes, second-writer exclusion, durable caught failures;
- bounded transient-provider recovery, attempt exhaustion, and immediate refusal
  of permanent authentication failures with redacted diagnostics;
- explicit preferred-provider exhaustion followed by a scope-identical fallback;
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
- durable direct/interactive/auto intake and cross-harness skill prompt loading;
- copywriting as a first-class specialist owner, shared conditional capability,
  and ordinary lane in the same integration lifecycle;
- prompt engineering and optimization as scoped specialists, including refusal
  of incomplete prompt contracts or missing, overlapping, over-budget,
  under-gain, self-scored, or unpromoted experiments;
- stdout-only typed metric/prompt receipts with stderr preserved as diagnostics,
  plus integrated-runtime prompt revalidation;
- refusal of pre-merge delivery commands and placeholder visual proof;
- exact review-issue target files bound to the routed owner's approved scope;
- one read-only initial-implementer receipt correction, refusal of
  correction-time writes, and resume normalization of a linear agent commit;
- immutable per-attempt contexts and private adapter/harness logs, native Claude
  transcript preservation, deduplicated Claude usage, and live activity metadata;
- one read-only repair-receipt correction and refusal of correction-time writes;
- fresh proof after repair, successful merge, target/config drift, finite-cap
  escalation, and explicit unlimited-review continuation.

CI runs the suite on Ubuntu and macOS with Python 3.10 and 3.14, compiles the
30-node policy graph, and validates it with the public Pi Graph Core release.
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
- [Engineering skill decisions](docs/ENGINEERING_SKILLS.md)
- [Prose skill decisions](docs/PROSE_SKILLS.md)
- [Contributing](CONTRIBUTING.md)
- [Security](SECURITY.md)
- [MIT license](LICENSE)
