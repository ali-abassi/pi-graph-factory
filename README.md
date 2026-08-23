# Pi Graph Factory

A deterministic, evidence-gated software factory built on
[Pi Graph Core](https://github.com/ali-abassi/pi-graph-core).

It turns a broad request, issue, or small change into a durable run:

```text
trigger → clarify → plan → explicit approval
        → 1–10 isolated implementers
        → integrate → tests + visual evidence → independent review
        → repair owner ─┐
             ↑         │ at most five cycles
             └─────────┘
        → guarded merge or human escalation
```

Agents do the judgment and coding; the controller owns order, limits,
receipts, approval, and merge authority. A model cannot skip a gate or declare
itself merged.

## What works today

- Existing repositories and newly initialized repositories.
- Durable request, answer, plan, approval, cycle, and merge state.
- Blocking clarification followed by a revised plan.
- Approval of the exact plan SHA-256, not a conversational “yes”.
- One to ten configured Pi, Claude Code, or Codex implementers.
- One Git branch and worktree per active implementer.
- Plan-time file ownership conflict rejection.
- Deterministic lane integration with `git cherry-pick` and `git diff --check`.
- A shared normalized agent receipt contract.
- Test, screenshot, and video receipts tied to an exact commit and plan.
- Reviewer findings routed back to the named owning implementer.
- Fresh evidence after every repair.
- Five review/repair cycles at most, followed by `human_required`.
- Fast-forward merge only after all gates pass and the target has not moved.
- Frozen config, repository, branch, plan, and evidence identity checks.

## Quick start

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

.venv/bin/python scripts/factory.py init \
  --repo /path/to/project --config factory.yaml --request-file request.md

.venv/bin/python scripts/factory.py plan \
  --run /path/to/project/.factory/runs/RUN_ID --file plan.json

# If the plan has blocking questions, answer them and submit a revised plan.
.venv/bin/python scripts/factory.py answer \
  --run /path/to/project/.factory/runs/RUN_ID \
  --question QUESTION_ID --answer "the user's answer"

.venv/bin/python scripts/factory.py approve \
  --run /path/to/project/.factory/runs/RUN_ID --sha256 PLAN_SHA256
.venv/bin/python scripts/factory.py run \
  --run /path/to/project/.factory/runs/RUN_ID
```

Use `--new-repo` when the target does not exist. Use `status` to read the
complete durable state. Every transition is appended to `events.jsonl`; the
terminal proof is `receipt.json`.

The planner submits a small typed contract:

```json
{
  "summary": "Build the requested feature",
  "tasks": [{
    "id": "api",
    "owner": "product",
    "files": ["src/api/**"],
    "acceptance": ["npm test"]
  }],
  "acceptance": ["npm test"],
  "risks": [],
  "open_questions": []
}
```

Each repair issue identifies an `owner`, so the controller routes it to the
right implementer rather than asking the whole team to redo the work.

## Configure agents

Edit [`factory.yaml`](factory.yaml) to set every agent's harness, model,
instruction file, skills, and tool allowlist. The example sends product work to
Pi and interface work to Claude Code. Only implementers owning approved tasks
launch, so a small request can use one agent and a broad plan up to ten.

Supported harness identifiers are `pi`, `claude-code`, and `codex`.
`scripts/agent_adapter.py` converts their final JSON into a common receipt. Pi
also records usage from its settled assistant event. Claude Code and Codex
currently return null usage fields unless the local harness output supplies
them; the factory records that honestly rather than estimating it.

## Visual proof

The target project owns browser or native UI automation. Its implementation
creates each screenshot and video declared under `evidence`, plus browser
receipts required by `test_commands`. The factory rejects missing or empty
files and failed commands, hashes every artifact, and binds the manifest to the
exact integration commit and approved plan.

The reviewer receives that manifest and must cite evidence in a typed `pass` or
`repair` verdict. Any repair makes the old proof stale, so capture and review
run again.

This is strong provenance, but not a universal browser recorder or pixel-level
quality oracle. Projects should use Playwright, native UI tests, or their
existing capture system to produce meaningful media and console/network logs.

## Merge policy

`merge.apply: false` is the default. A passing run ends at `merge_ready` with a
merge-authorizing receipt but does not alter the target. Set it to `true` for
automatic fast-forward merge.

Merge is impossible unless:

1. the current plan is the exact approved plan;
2. the frozen contract and target repository still match;
3. the independent final review passes with no open issues;
4. tests pass and evidence belongs to the current integration commit;
5. the target branch has not moved and the checkout is clean; and
6. `git diff --check` passes.

## Verify it

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/compile_factory.py factory.yaml --out steps.yaml
/path/to/pi-graph-core/bin/piw validate steps.yaml --strict
```

Tests exercise clarification, wrong-digest rejection, isolated implementation,
review-directed repair, evidence recapture, successful merge, ownership
conflicts, frozen-contract drift, and five-cycle human escalation.

## Deliberate remaining gaps

- GitHub issue/webhook ingestion is an adapter around `factory.py init`; it is
  not bundled yet.
- Planner conversation uses typed `plan` and `answer` commands; a hosted chat
  UI is not bundled yet.
- Semantic screenshot quality and video-duration validation belong to the
  configured review and capture harness today.
- Execution is local. Production still needs sandboxing, secret isolation,
  concurrency locks, cancellation, and remote job recovery.
- Cross-lane cherry-pick conflicts stop for a human; autonomous integration
  conflict repair is not included.

Those boundaries are intentional. The repo proves the core factory contract
without pretending it is already a hosted, unattended platform.
