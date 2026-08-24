# Intake modes

Pi Graph Factory accepts three intake modes. They all converge on the same
planner, independent plan judge, exact-hash authorization, implementation,
proof, review, and merge lifecycle.

```text
raw idea
  |-- interactive: a person answers consequential questions
  |-- auto: an agent resolves discoverable and reversible choices
  `-- direct: the request is already execution-ready
                         |
                  durable intake artifact
                         |
                  factory planning begins
```

The controller does not reimplement an interview system. Intake producers are
adapters at the edge; the factory validates and preserves their artifacts before
planning. This keeps the public repository independent of any private skill
installation or provider.

## Interactive

Use interactive mode for broad ideas where product-defining choices should stay
human-led. In an Agent X environment:

- `/grill-me` is the bounded phone interview and produces `goal-brief.md`.
- `goal-grill` is the text-interview alternative and produces the same brief
  contract.
- `/grill-with-docs` is the same interactive path with durable domain modeling:
  it updates `CONTEXT.md`/`CONTEXT-MAP.md` and creates an ADR only for a
  surprising, hard-to-reverse tradeoff. It still produces the same Goal Brief,
  so the factory does not need another intake mode.

When the docs-enabled path changes files in the target repository, review and
commit them before initialization. The enriched Graphify pass then includes
those docs in the planner's repository map.

The brief must be classified `Ready` or `Ready With Assumptions` and contain the
required objective, evidence, scope, orchestration, validation, approval, and
stop-condition sections.

```bash
.venv/bin/python scripts/factory.py start \
  --repo /path/to/project \
  --intake-mode interactive \
  --request-file /path/to/goal-brief.md
```

## Auto

Use auto mode when the operator wants the agent to make the best defensible
choices instead of asking routine questions. In Agent X, `/grill-yourself`
produces `self-grilled-brief.md` and `self-grill.json`.

Auto does not mean guessing. The producer must inspect available evidence, run
the relevant question tree internally, prefer the smallest coherent reversible
default, label every inference/default, record what would overturn it, and
red-team the result. The controller then checks that:

- intent, audience, scope, experience, taste, architecture, and validation are
  covered;
- material decisions include basis, confidence, reversibility, implications,
  and overturning evidence;
- no low-confidence moderate/hard-to-reverse decision was self-approved; and
- no human-only decision remains unresolved.

```bash
.venv/bin/python scripts/factory.py start \
  --repo /path/to/project \
  --intake-mode auto \
  --request-file /path/to/self-grilled-brief.md \
  --intake-ledger /path/to/self-grill.json
```

If a genuinely consequential human-only decision remains, initialization fails.
Resolve only that decision interactively, regenerate the artifacts, and retry.
The factory never interprets autonomous mode as publication, spending,
deployment, destructive-action, credential, legal, or other missing authority.

## Direct

Use direct mode for a sufficiently specific issue, bug, or small request. This
is the backward-compatible default:

```bash
.venv/bin/python scripts/factory.py start \
  --repo /path/to/project \
  --request 'Fix CSV export for quoted line breaks and add a regression test.'
```

Direct mode deliberately avoids ceremony when the task is already resolved.

With the default judge authority, `start` owns every downstream transition.
Planner uncertainty is returned to the planner as bounded revision feedback; the
planner must choose and document the safest evidence-backed reversible assumption
before the independent judge may authorize implementation. Use `init` when
inspecting stages manually, and `approval.mode: human` only when governance
deliberately requires a separate exact-hash approval.

## Durable handoff

Every mode writes its canonical input under `.factory/runs/RUN_ID/intake/`,
stores content hashes and readiness in `state.json`, and includes intake
provenance in the planner context. `factory inspect` lists the preserved intake
artifacts. Under the default judge authority, the planner cannot create a human
checkpoint. It must resolve uncertainty from the available context, record the
assumption and its reversal condition, and submit the revised plan to the judge.
